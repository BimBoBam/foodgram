from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.reverse import reverse

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import LimitPagination
from api.permissions import IsAdminAuthorOrReadOnly
from api.serializers import (AvatarSerializer, FavoriteRecipeSerializer,
                             IngredientSerializer, RecipeReadSerializer,
                             RecipeWriteSerializer, SerializerUser,
                             ShoppingListSerializer,
                             SubscriberDetailSerializer, SubscriberSerializer,
                             TagSerializer)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)
from users.models import Follow

User = get_user_model()


class ViewSetUser(UserViewSet):
    queryset = User.objects.all()
    serializer_class = SerializerUser
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = LimitPagination

    @action(['get'], detail=False, permission_classes=(IsAuthenticated,))
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        return self.retrieve(request, *args, **kwargs)

    @action(
        ['put'],
        detail=False,
        permission_classes=(IsAdminAuthorOrReadOnly,),
        url_path='me/avatar',
    )
    def avatar(self, request, *args, **kwargs):
        serializer = AvatarSerializer(
            instance=request.user,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request, *args, **kwargs):
        user = self.request.user
        user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('GET',),
        permission_classes=(IsAuthenticated,),
        url_path='subscriptions',
        url_name='subscriptions',
    )
    def subscriptions(self, request):
        user = request.user
        queryset = queryset = user.follower.all()
        pages = self.paginate_queryset(queryset)
        serializer = SubscriberDetailSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post', 'delete'),
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)
        data = {'user': user.id, 'author': author.id}
        if request.method == 'POST':
            serializer = SubscriberSerializer(data=data,
                                              context={'request': request})
            serializer.is_valid(raise_exception=True)
            subscription = serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )
        subscription = Follow.objects.filter(user=user, author=author)
        if not subscription.exists():
            raise serializers.ValidationError()
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAdminAuthorOrReadOnly,)
    pagination_class = None
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    search_fields = ('^name',)


class shop_and_fav():
    @staticmethod
    def for_post(request, w_ser, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        serializer = w_ser(data={
            'user': user.id,
            'recipe': recipe.id},
            context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    def for_del(request, w_mod, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        entry = w_mod.objects.filter(user=user, recipe=recipe)
        if not entry.exists():
            raise serializers.ValidationError()
        entry.delete()


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminAuthorOrReadOnly,)
    queryset = Recipe.objects.all()
    pagination_class = LimitPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'get-link'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=['GET'],
        permission_classes=[AllowAny],
        url_path='get-link',
        url_name='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        rev_link = reverse('short_url', args=[recipe.pk])
        return Response({'short-link': request.build_absolute_uri(rev_link)},
                        status=status.HTTP_200_OK,)

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart',
        url_name='shopping_cart',
    )
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return Response(shop_and_fav.for_post(request,
                                                  ShoppingListSerializer,
                                                  pk),
                            status=status.HTTP_201_CREATED)
        shop_and_fav.for_del(request, ShoppingList, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def shopping_list_to_txt(ingredients):
        return '\n'.join(
            f'{ingredient["ingredient__name"]} - {ingredient["sum"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            for ingredient in ingredients
        )

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart',
        url_name='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__shopping_lists__user=request.user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(sum=Sum('amount'))
        )
        shopping_list = self.shopping_list_to_txt(ingredients)
        return HttpResponse(shopping_list, content_type='text/plain')

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated],
        url_path='favorite',
        url_name='favorite',
    )
    def favorite(self, request, pk):
        if request.method == 'POST':
            return Response(shop_and_fav.for_post(request,
                                                  FavoriteRecipeSerializer,
                                                  pk),
                            status=status.HTTP_201_CREATED)
        shop_and_fav.for_del(request, Favorite, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@require_GET
def short_url(request, pk):
    try:
        Recipe.objects.filter(pk=pk).exists()
        return redirect(f'/recipes/{pk}/')
    except Exception:
        raise ValidationError(f'Recipe "{pk}" does not exist.')
