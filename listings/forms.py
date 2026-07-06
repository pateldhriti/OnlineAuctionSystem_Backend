from django import forms

from .models import Listing


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'description', 'category', 'starting_price', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'starting_price': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}
            ),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_starting_price(self):
        starting_price = self.cleaned_data['starting_price']
        if starting_price <= 0:
            raise forms.ValidationError('Starting price must be greater than zero.')
        return starting_price
