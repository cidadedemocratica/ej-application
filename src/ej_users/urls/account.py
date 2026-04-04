from allauth.account import views as allauth
from django.contrib.auth.decorators import login_required
from django.urls import path, reverse_lazy
from ..views import account

app_name = "ej_users"
account_url = "account/"

urlpatterns = [
    path(
        f"{account_url}",
        account.IndexView.as_view(),
        name="index",
    ),
    path(
        f"{account_url}logout/",
        account.LogoutView.as_view(),
        name="logout",
    ),
    path(
        f"{account_url}remove/",
        account.RemoveAccountView.as_view(),
        name="remove-account",
    ),
    path(
        f"{account_url}change-password/",
        login_required(
            allauth.PasswordChangeView.as_view(
                success_url=reverse_lazy("account:change-password")
            )
        ),
        name="change-password",
    ),
    path(
        f"{account_url}manage-email/",
        login_required(
            allauth.EmailView.as_view(
                success_url=reverse_lazy("account:manage-email")
            )
        ),
        name="manage-email",
    ),
]
