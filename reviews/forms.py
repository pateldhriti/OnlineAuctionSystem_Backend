from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Share your experience...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment'].widget.attrs['class'] = 'form-control'
        self.fields['rating'].required = True
