import base64
from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer
from rest_framework import serializers
from django.shortcuts import get_object_or_404
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Tag, Ingredient, IngredientInRecipe, Recipe,
                            Subscribe, Favorite, ShoppingCart)
from users.models import User

from django.db.models import Count


class RecipeShortLisTSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return Subscribe.objects.filter(
            user_id=user.id, author_id=obj.id
        ).exists()


class SubscribeGetSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',)

    def get_recipes(self, obj):
        recipes_limit = self.context['request'].GET.get('recipes_limit')
        if recipes_limit is not None:
            recipes_limit = int(recipes_limit)
        recipes = obj.recipes.all()[:recipes_limit]
        serializer = RecipeShortLisTSerializer(recipes, many=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.annotate(num_recipes=Count('author')).count()

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return Subscribe.objects.filter(
            user_id=user.id, author_id=obj.id
        ).exists()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeGetSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="ingredient.name")
    measurement_unit = serializers.CharField(
       source='ingredient.measurement_unit')

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount', 'name', 'measurement_unit',)
        # fields = '__all__'


class IngredientInRecipeCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount',)


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class RecipeGetSerializer(serializers.ModelSerializer):
    # author = serializers.SlugRelatedField(
    #      slug_field='username', read_only=True)
    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeGetSerializer(many=True, read_only=True)
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id',
                  'tags',
                  'author',
                  'ingredients',
                  'is_favorited',
                  'is_in_shopping_cart',
                  'name',
                  'image',
                  'text',
                  'cooking_time',)

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return Favorite.objects.filter(
            user_id=user.id, recipe_id=obj.id
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return ShoppingCart.objects.filter(
            user_id=user.id, recipe_id=obj.id
        ).exists()


class RecipeModifySerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all())
    ingredients = IngredientInRecipeCreateSerializer(many=True)
    #image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('ingredients',
                  'tags',
                  'name',
                  #'image',
                  'text',
                  'cooking_time',)
