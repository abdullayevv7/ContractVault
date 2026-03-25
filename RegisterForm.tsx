"""
Custom pagination classes for ContractVault API.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class StandardPagination(PageNumberPagination):
    """Standard pagination with configurable page size."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("current_page", self.page.number),
                    ("page_size", self.get_page_size(self.request)),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "example": 100},
                "total_pages": {"type": "integer", "example": 5},
                "current_page": {"type": "integer", "example": 1},
                "page_size": {"type": "integer", "example": 20},
                "next": {"type": "string", "nullable": True},
                "previous": {"type": "string", "nullable": True},
                "results": schema,
            },
        }


class SmallPagination(StandardPagination):
    """Smaller page size for nested resources."""

    page_size = 10
    max_page_size = 50
