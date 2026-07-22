from django import forms
from django.utils import timezone

from .models import Listing

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ENDS_AT_INPUT_FORMAT = '%Y-%m-%dT%H:%M'


class ListingForm(forms.ModelForm):
    ends_at = forms.DateTimeField(
        required=False,
        label='Bidding expiry time',
        help_text='Leave blank to use the default 7-day auction.',
        input_formats=[ENDS_AT_INPUT_FORMAT],
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format=ENDS_AT_INPUT_FORMAT,
        ),
    )

    class Meta:
        model = Listing
        fields = ['title', 'description', 'category', 'starting_price', 'ends_at', 'image']
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

    def clean_ends_at(self):
        ends_at = self.cleaned_data.get('ends_at')
        if ends_at and ends_at <= timezone.now():
            raise forms.ValidationError('Bidding expiry time must be in the future.')
        return ends_at

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and image.size > MAX_IMAGE_SIZE_BYTES:
            raise forms.ValidationError('Image must be smaller than 5MB.')
        return image
