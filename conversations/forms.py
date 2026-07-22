from django import forms

from .models import Message


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['body']
        widgets = {
            # CharField/TextField form fields strip whitespace by default, so
            # a whitespace-only submission is already rejected as "required"
            # without any extra validation here.
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write a message…'}),
        }
