from django import forms
from .models import *
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = '__all__'

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['due_date'].widget = forms.DateInput(attrs={'type': 'date'})

class ProduceForm(forms.ModelForm):
    class Meta:
        model = Produce
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Extract the user from kwargs
        super().__init__(*args, **kwargs)

        if user and user.user_type != 'admin':
            # Filter dealers by the user's branch
            self.fields['dealer'].queryset = Dealer.objects.filter(branch=user.branch)    
        
    def clean(self):
        cleaned_data = super().clean()
        type = cleaned_data.get('type')

        if type:
            type = type.lower() # ensures it matches even if the user chooses "Beans" or "beans".
            if type == 'beans':
                cleaned_data['buying_price'] = 2800
                cleaned_data['selling_price'] = 3300
            elif type == 'maize':
                cleaned_data['buying_price'] = 1000
                cleaned_data['selling_price'] =2000
            elif type == 'g-nuts':
                cleaned_data['buying_price'] = 5000
                cleaned_data['selling_price'] = 7000
            elif type == 'soybeans':
                cleaned_data['buying_price'] = 2000
                cleaned_data['selling_price'] = 3000
            elif type == 'cowpeas':
                cleaned_data['buying_price'] = 2500
                cleaned_data['selling_price'] = 4000
        return cleaned_data


    

class ProcurementForm(forms.ModelForm):
     minimum_quantity = forms.FloatField(
        required=False,
        label="Minimum Quantity (optional)",
        help_text="Set a minimum stock level for this product at this branch."
    )
     class Meta:
        model = Procurement
        fields = '__all__'  # Keeps existing fields like produce, dealer, etc.
        

     def __init__(self, *args, **kwargs):
        super(ProcurementForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

     def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['expected_delivery_date'].widget = forms.DateInput(attrs={'type': 'date'})
            self.fields['actual_delivery_date'].widget = forms.DateInput(attrs={'type': 'date'})


    


class UserCreation(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = '__all__'
    def save(self, commit=True):
        user = super(UserCreation, self).save(commit=False)
        if commit:
            user.is_active = True
            user.is_staff = True
            # Save the user instance to the database
            user.save()
       
        return user
    

User = get_user_model()

class CustomUserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'user_type', 'branch', 'is_active', 'is_staff']



class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'bg-[#8777BA] w-full p-2.5 rounded-md placeholder:text-gray-300 shadow-md shadow-blue-950 text-white',
            'placeholder': 'Enter username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'bg-[#8777BA] w-full p-2.5 rounded-md placeholder:text-gray-300 shadow-md shadow-blue-950 text-white',
            'placeholder': 'Enter password'
        })
    )        