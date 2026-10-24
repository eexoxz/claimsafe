from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from .models import FoundItem, User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text="Use a contact address you control. This prototype does not send email.")
    privacy_acknowledged = forms.BooleanField(label="I have read the privacy and safe-use guidance.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This address cannot be used. Choose another address or sign in.")
        return email

    def clean_username(self):
        username = super().clean_username()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is unavailable.")
        return username


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=150)


class ItemForm(forms.ModelForm):
    identifying_details = forms.CharField(
        min_length=10, max_length=2000, widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Private: record distinctive marks or contents. Never record device passwords or access PINs.",
    )

    class Meta:
        model = FoundItem
        fields = ("title", "category", "location", "found_on", "public_description")
        widgets = {
            "found_on": forms.DateInput(attrs={"type": "date"}),
            "public_description": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {"public_description": "Public: keep identifying marks, full serial numbers and personal details out of this description."}

    def clean_found_on(self):
        date = self.cleaned_data["found_on"]
        if date > timezone.localdate():
            raise forms.ValidationError("The found date cannot be in the future.")
        return date


class ClaimForm(forms.Form):
    proof = forms.CharField(
        label="Describe what makes this item yours", min_length=20, max_length=2000,
        widget=forms.Textarea(attrs={"rows": 6}),
        help_text="Give details not shown in the listing. Do not include passwords, PINs, ID numbers or financial information.",
    )
    truthful = forms.BooleanField(label="These details are accurate and I understand staff must review my claim.")


class ReviewForm(forms.Form):
    decision = forms.ChoiceField(choices=[("approve", "Approve claim"), ("reject", "Do not approve")])
    note = forms.CharField(
        label="Message to claimant", min_length=10, max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="The claimant can read this message. Do not reveal withheld item details or another person's information.",
    )


class CollectionForm(forms.Form):
    token = forms.CharField(label="Claimant's collection code", min_length=20, max_length=80, strip=True,
                            widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}))
    identity_checked = forms.BooleanField(label="I have checked this is the approved claimant and confirmed the handover in person.")
