from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Expense
from django.core.exceptions import ValidationError
from .models import GroupMember
from django.core.validators import MinValueValidator

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required. Enter a valid email address.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()  # Normalize to lowercase
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()  # Ensure lowercase email is saved
        if commit:
            user.save()
        return user





class ExpenseForm(forms.ModelForm):
    amount = forms.DecimalField(
        validators=[MinValueValidator(0.01, message="Amount must be positive")],
        widget=forms.NumberInput(attrs={
            'min': '0.01',
            'oninput': 'this.value = Math.abs(this.value)'
        })
    )
    involved_members = forms.ModelMultipleChoiceField(
        queryset=GroupMember.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = Expense
        fields = ['name', 'amount', 'category', 'involved_members']

    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)
        if group:
            queryset = GroupMember.objects.filter(group=group)
            self.fields['involved_members'].queryset = queryset
            self.fields['involved_members'].label_from_instance = lambda obj: obj.user.username
            self.fields['involved_members'].initial = queryset