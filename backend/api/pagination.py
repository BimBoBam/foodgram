from rest_framework.pagination import PageNumberPagination

from foodgram import constants as c


class LimitPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    page_size = c.PAGE_SIZE