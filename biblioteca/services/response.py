import logging

from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

logger = logging.getLogger(__name__)


class Result:
    @staticmethod
    def Exitosa(Mensaje, data=None, status=HTTP_200_OK):
        return Response({"success": True, "Mensaje": Mensaje, "datos": data}, status=status)

    @staticmethod
    def ResponsePaginator(Mensaje, data, total_pages=0, page=1, button_previous=False, button_next=False):
        return Response({"success": True, "Mensaje": Mensaje, 'datos': data, 'maxPages': total_pages,
                         'currentpage': page, 'previous': button_previous, 'next': button_next}, status=HTTP_200_OK)

    @staticmethod
    def ErrorResponsePaginator(Mensaje, total_pages, page):
        return Response({"success": False, "Mensaje": Mensaje, 'datos': '', 'maxPages': total_pages,
                         'currentpage': page,
                         'previous': False, 'next': False}, status=HTTP_400_BAD_REQUEST)

    @staticmethod
    def Error(Mensaje, status=HTTP_400_BAD_REQUEST):
        return Response({"success": False, "Mensaje": Mensaje, "datos": None}, status=status)


def TryCatch(action_to_execute, *args, **kwargs):
    try:
        return action_to_execute(*args, **kwargs)
    except Exception:
        logger.exception("Error interno en TryCatch")
        return Response({"success": False, "Mensaje": "Error interno del servidor", "datos": None},
                        status=HTTP_500_INTERNAL_SERVER_ERROR)
