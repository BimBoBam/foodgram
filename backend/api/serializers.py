from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField

from foodgram import constants as c
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            RecipeTags, ShoppingList, Tag)
from users.models import Follow

User = get_user_model()


class SerializerUser(UserSerializer):

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(allow_null=True, required=False)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and request.user.follower.filter(author=obj).exists())

    def validate(self, data):
        user = self.context['request'].user
        author = data.get('author')
        if user == author:
            raise ValidationError("You can't subscribe to yourself.")
        if Follow.objects.filter(user=user, author=author).exists():
            raise ValidationError("You already follow this user.")
        return data


class SerializerUserCreate(UserCreateSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
        )


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount'
        )

    def validate_id(self, value):
        return get_object_or_404(Ingredient, id=value)


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):

    tags = TagSerializer(many=True)
    author = SerializerUser()
    ingredients = RecipeIngredientSerializer(
        source='ingredient_list',
        many=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def check_user_status(self, obj, model_class):
        user = self.context.get('request')
        return (
            user
            and user.user.is_authenticated
            and model_class.objects.filter(recipe=obj,
                                           user=user.user).exists()
        )

    def get_is_favorited(self, obj):
        return self.check_user_status(obj, Favorite)

    def get_is_in_shopping_cart(self, obj):
        return self.check_user_status(obj, ShoppingList)


class RecipeWriteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        label='Tags',
    )
    ingredients = RecipeIngredientWriteSerializer(
        many=True,
        label='Ingredients',
    )
    image = Base64ImageField(
        allow_null=True,
        label='images'
    )

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                'Please add tag')

        if len(value) != len(set(value)):
            raise serializers.ValidationError('Tags must be unique')

        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Please add ingredient'
            )
        ingredient_ids = [ingredient['id'] for ingredient in value]
        existing_ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
        if len(existing_ingredients) != len(ingredient_ids):
            missing_ids = set(ingredient_ids) - set(
                existing_ingredients.values_list('id', flat=True)
            )
            raise serializers.ValidationError(
                f'Ingredients with id {missing_ids} do not exist'
            )
        return value

    def to_representation(self, instance):
        serializer = RecipeReadSerializer(
            instance, context={'request': self.context.get('request')}
        )
        return serializer.data

    def create_tags(self, tags, recipe):
        recipe.tags.set(tags)

    def create_ingredients(self, ingredients, recipe):
        recipe_ingredients = []
        for ingredient_data in ingredients:
            ingredient_id = ingredient_data['id']
            ingredient = Ingredient.objects.get(pk=ingredient_id)
            amount = ingredient_data['amount']
            recipe_ingredients.append(
                RecipeIngredient(ingredient=ingredient,
                                 recipe=recipe, amount=amount)
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        user = self.context.get('request').user
        recipe = Recipe.objects.create(**validated_data, author=user)
        self.create_tags(tags, recipe)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        RecipeTags.objects.filter(recipe=instance).delete()
        RecipeIngredient.objects.filter(recipe=instance).delete()
        self.create_tags(validated_data.pop('tags'), instance)
        self.create_ingredients(validated_data.pop('ingredients'), instance)
        return super().update(instance, validated_data)


class ShortRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriberDetailSerializer(SerializerUser):
    email = serializers.ReadOnlyField(source='author.email')
    id = serializers.ReadOnlyField(source='author.id')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = Base64ImageField(source='author.avatar')

    class Meta:
        model = User
        fields = SerializerUser.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit', c.PAGE_SIZE)
        if limit.isdigit():
            limit = int(limit)
        else:
            limit = c.PAGE_SIZE
        return ShortRecipeSerializer(
            obj.recipes.all()[:limit],
            many=True,
            context={'request': request},
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class SubscriberSerializer(serializers.ModelSerializer):

    class Meta:
        model = Follow
        fields = 'author'

    def to_representation(self, instance):
        return SubscriberDetailSerializer(instance, context=self.context).data

    def validate_author(self, value):
        if self.context['request'].user == value:
            raise serializers.ValidationError(
                'You cannot follow yourself')
        return value


class FavoriteRecipeSerializer(ShortRecipeSerializer):
    image = Base64ImageField()

    def validate(self, data):
        user = self.context['request'].user
        recipe = data.get('recipe')
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                f'Recipe "{recipe.name}" is already in favorites.'
            )
        return data

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'user': instance.user.username,
            'recipe': instance.recipe.id,
        }


class ShoppingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingList
        fields = ('user', 'recipe')

    def validate(self, data):
        user = self.context['request'].user
        recipe = data.get('recipe')

        if ShoppingList.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                f'Recipe "{recipe.name}" is already in the shopping list.'
            )
        return data

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'user': instance.user.username,
            'recipe': instance.recipe.id,
        }
