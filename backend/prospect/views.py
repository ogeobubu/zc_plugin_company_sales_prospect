from common.utils import centrifugo_post
import requests
import json

from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.core.paginator import Paginator

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .serializers import ProspectSerializer, ProspectUpdateSerializer
# changed the import to a single import
from common.utils import centrifugo_post
from rest_framework.permissions import AllowAny
from common.utils import isAuthorized
from common.utils import isValidOrganisation

PLUGIN_ID = settings.PLUGIN_ID
ORGANISATION_ID = settings.ORGANISATION_ID
# Create your views here.


class WelcomeView(APIView):
    def get(self, request, *args, **kwargs):
        """
        this functions sends a welcome email to new leads
        still in development stage
        would configure it properly during production
        """
        send_mail(
            subject=f"Welcome {request.user}",
            message=f"Hello {request.user} your account was successfully created",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=["test1@dummy.com"],
        )
        return JsonResponse({"message": "welcome mail has been sent successfully"})


def SearchProspects(request, search):

    # # check authentication
    # if not isAuthorized(request):
    #     return Response(data={"message":"Missing Cookie/token header or session expired"}, status=status.HTTP_401_UNAUTHORIZED)

    # if not isValidOrganisation(ORGANISATION_ID, request):
    #     return Response(data={"message":"Invalid/Missing organization id"}, status=status.HTTP_401_UNAUTHORIZED)

    # import requests
    url = f"https://api.zuri.chat/data/read/{PLUGIN_ID}/prospects/{ORGANISATION_ID}/"
    response = requests.request("GET", url)
    r = response.json()
    # response code should be 200
    if response.status_code == 200:
        liste = []
        for i in r["data"]:
            if (
                (search in i["first_name"])
                or (search in i["last_name"])
                or (search in i["email"])
                or (search in i["company"])
            ):
                liste.append(i)
        return JsonResponse(liste, safe=False)


class ProspectsListView(APIView):
    serializer_class = ProspectSerializer
    queryset = None
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        # # check authentication
        if not isAuthorized(request):
            return Response(data={"message": "Missing Cookie/token header or session expired"}, status=status.HTTP_401_UNAUTHORIZED)

        if not isValidOrganisation(ORGANISATION_ID, request):
            return Response(data={"message": "Invalid/Missing organization id"}, status=status.HTTP_401_UNAUTHORIZED)

        url = f"https://api.zuri.chat/data/read/{PLUGIN_ID}/prospects/{ORGANISATION_ID}"
        response = requests.request("GET", url)
        if response.status_code == 200:
            r = response.json()
            # centrifugo_post("Prospects", {"event": "join", "token": "elijah"})
            # serializer = ProspectSerializer(data=r['data'], many=True)
            # serializer.is_valid(raise_exception=True)
            paginator = Paginator(r["data"], self.paginate_by)
            page_num = request.query_params.get('page', 1)
            page_obj = paginator.get_page(page_num)
            paginated_data = {
                "contacts": list(page_obj),
                "pageNum": page_obj.number,
                "next": page_obj.has_next(),
                "prev": page_obj.has_previous(),
            }
            return Response(data=paginated_data, status=status.HTTP_200_OK)
        return Response(
            data={"message": "Try again later"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ProspectsCreateView(APIView):
    """
    Documentation here.
    """

    serializer_class = ProspectSerializer
    queryset = None

    def post(self, request, *args, **kwargs):
        # # check authentication
        if not isAuthorized(request):
            return Response(data={"message": "Missing Cookie/token header or session expired"}, status=status.HTTP_401_UNAUTHORIZED)

        if not isValidOrganisation(ORGANISATION_ID, request):
            return Response(data={"message": "Invalid/Missing organization id"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ProspectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = "https://api.zuri.chat/data/write"
        name = request.data.get("name")
        email = request.data.get("email")
        phone_number = request.data.get("phone_number")
        company = request.data.get("company")
        data = {
            "plugin_id": PLUGIN_ID,
            "organization_id": ORGANISATION_ID,
            "collection_name": "prospects",
            "bulk_write": False,
            "payload": {
                "name": name,
                "phone_number": phone_number,
                "email": email,
                "company": company,
            },
        }
        response = requests.request("POST", url, data=json.dumps(data))
        r = response.json()
        print(response.status_code)
        if response.status_code == 201:
            new_prospect = request.data
            # request.data._mutable = True
            # new_prospect["_id"] = r["data"]["object_id"]
            # request.data._mutable = False

            # new_prospect["_id"] = r["data"]["object_id"]
        #     # centrifugo_post(
        #     #     "Prospects",
        #     #     {"event": "new_prospect", "token": "elijah", "object": new_prospect},
        #     # )
            print(response.status_code)
            return Response(data=r, status=status.HTTP_201_CREATED)
        return Response(
            data={"message": "Try again later"},
            status=response.status_code,
        )


class ProspectsUpdateView(APIView):
    serializer_class = ProspectSerializer
    queryset = None

    def put(self, request, *args, **kwargs):
        # check authorization
        if not isAuthorized(request):
            return Response(data={"message": "Missing Cookie/token header or session expired"}, status=status.HTTP_401_UNAUTHORIZED)

        if not isValidOrganisation(ORGANISATION_ID, request):
            return Response(data={"message": "Invalid/Missing organization id"}, status=status.HTTP_401_UNAUTHORIZED)

        url = "https://api.zuri.chat/data/write"
        serializer = ProspectUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        object_id = serializer.data.pop("object_id")
        data = {
            "plugin_id": PLUGIN_ID,
            "organization_id": ORGANISATION_ID,
            "collection_name": "prospects",
            "bulk_write": False,
            "object_id": object_id,
            "payload": serializer.data,
        }
        response = requests.put(url, data=json.dumps(data))

        if response.status_code in [200, 201]:
            r = response.json()
            if r["data"]["matched_documents"] == 0:
                return Response(
                    data={"message": "There is no prospect with the 'object_id' you supplied."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if r["data"]["modified_documents"] == 0:
                return Response(
                    data={"message": "Prospect update failed. Empty data or invalid values was passed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            centrifugo_post(
                "Prospects",
                {
                    "event": "edit_prospect",
                    "token": "elijah",
                    "object": serializer.data,
                },
            )
            return Response(data=r, status=status.HTTP_200_OK)

        return Response(
            data={"message": "Try again later", "data": request.data},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ProspectsBatchDeleteView(APIView):

    def delete(self, request, **kwargs):
        # check authentication
        if not isAuthorized(request):
            return Response(data={"message": "Missing Cookie/token header or session expired"}, status=status.HTTP_401_UNAUTHORIZED)

        if not isValidOrganisation(ORGANISATION_ID, request):
            return Response(data={"message": "Invalid/Missing organization id"}, status=status.HTTP_401_UNAUTHORIZED)
        filterData = request.data.get('filter')

        url = "https://api.zuri.chat/data/delete"
        data = {
            "bulk_delete": True,
            "plugin_id": PLUGIN_ID,
            "organization_id": ORGANISATION_ID,
            "collection_name": "prospects",
            "filter": {
                "email": {
                    "$in": filterData
                }
            }
        }

        response = requests.request("POST", url, data=json.dumps(data))
        if response.status_code == 200:
            r = response.json()
            if r["data"]["deleted_count"] == 0:
                return Response(
                    data={
                        "message": "There is no prospect with this object id you supplied"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            centrifugo_post(
                "Prospects",
                {
                    "event": "delete_prospect",
                    "token": "elijah",
                    "object": filterData,
                },
            )
            return Response(data={"message": " Prospect list  deleted successful"}, status=status.HTTP_200_OK)
        return Response(
            data={"message": "Try again later"},
            status=status.HTTP_400_BAD_REQUEST
        )


class ProspectsDeleteView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def delete(self, request, search, *args, **kwargs):
        # # check authentication
        if not isAuthorized(request):
            return Response(data={"message": "Missing Cookie/token header or session expired"}, status=status.HTTP_401_UNAUTHORIZED)

        if not isValidOrganisation(ORGANISATION_ID, request):
            return Response(data={"message": "Invalid/Missing organization id"}, status=status.HTTP_401_UNAUTHORIZED)

        url = "https://api.zuri.chat/data/delete"
        data = {
            "plugin_id": PLUGIN_ID,
            "organization_id": ORGANISATION_ID,
            "collection_name": "prospects",
            "object_id": search,
        }
        response = requests.request("POST", url, data=json.dumps(data))
        print(response.text)
        if response.status_code == 200:
            r = response.json()
            if r["data"]["deleted_count"] == 0:
                return Response(
                    data={
                        "message": "There is no prospect with this object id you supplied"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            centrifugo_post(
                "Prospects",
                {
                    "event": "delete_prospect",
                    "token": "elijah",
                    "id": kwargs.get("object_id"),
                },
            )
            return Response(data={"message": "successful"}, status=status.HTTP_200_OK)
        return Response(
            data={"message": "Try again later"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
