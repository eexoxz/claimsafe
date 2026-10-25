from django.urls import path
from . import views
from . import account_views

urlpatterns = [
    path("account/security/", account_views.account_security, name="account_security"),
    path("account/password/", account_views.password_change, name="password_change"),
    path("account/recover/", account_views.account_recovery, name="account_recovery"),
    path("account/verify/", account_views.mfa_challenge, name="mfa_challenge"),
    path("account/authenticator/", account_views.mfa_setup, name="mfa_setup"),
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.sign_in, name="login"),
    path("logout/", views.sign_out, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("privacy/", views.privacy, name="privacy"),
    path("items/new/", views.item_new, name="item_new"),
    path("items/<uuid:pk>/", views.item_detail, name="item_detail"),
    path("items/<uuid:pk>/claim/", views.claim_new, name="claim_new"),
    path("claims/<uuid:pk>/", views.claim_detail, name="claim_detail"),
    path("claims/<uuid:pk>/review/", views.review, name="review"),
    path("claims/<uuid:pk>/code/", views.issue_code, name="issue_code"),
    path("claims/<uuid:pk>/collect/", views.collect, name="collect"),
    path("desk/", views.staff_queue, name="staff_queue"),
    path("activity/", views.audit_dashboard, name="audit"),
    path("accounts/", views.users, name="users"),
    path("accounts/<int:pk>/toggle/", views.toggle_user, name="toggle_user"),
]
