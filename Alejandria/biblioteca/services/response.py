from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST,HTTP_200_OK

class Result():
    def Exitosa(Mensaje,data, status):
        return Response({"success": True, "Mensaje": Mensaje, "datos":data, "status": status})

    def ResponsePaginator(Mensaje, data, total_pages=0, page=1, button_previous = False,button_next=False):
        return Response({"success": True, "Mensaje": Mensaje, 'datos': data, 'maxPages': total_pages,
                     'currentpage': page, 'previous':button_previous, 'next':button_next,  "status": HTTP_200_OK})

    def ErrorResponsePaginator(Mensaje, total_pages, page):
        return Response({"success": False, "Mensaje": Mensaje, 'datos': '', 'maxPages': total_pages,
                         'currentpage': page,
                          'previous': False, 'next': False, "status": HTTP_400_BAD_REQUEST})

    def Error(Mensaje):
        return Response({"success": False, "Mensaje": Mensaje, "datos":"", "status": HTTP_400_BAD_REQUEST})

class ListError():
    Mensaje=[]
    def Error(Mensaje=[]):
        return Response({"success": False, "Mensaje": Mensaje, "datos":"", "status": HTTP_400_BAD_REQUEST})

def TryCatch(action_to_execute, *args, **kwargs):
    try:
        return action_to_execute(*args, **kwargs)
    except Exception as e:
        return Result.Error(f"Unexpected error: {str(e)}")