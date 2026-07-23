from django import forms

from .models import AutoBid, Bid


class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, listing=None, bidder=None, **kwargs):
        self.listing = listing
        self.bidder = bidder
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Bid amount must be greater than zero.')
        return amount

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        if amount is None or self.listing is None:
            return cleaned_data

        if not self.listing.is_active or self.listing.has_ended:
            raise forms.ValidationError('This listing is no longer accepting bids.')

        if self.bidder is not None and self.listing.seller_id == self.bidder.pk:
            raise forms.ValidationError('You cannot bid on your own listing.')

        minimum = Bid.current_price_for(self.listing)
        if amount <= minimum:
            raise forms.ValidationError(
                'Your bid must be higher than the current price of $%(minimum)s.',
                params={'minimum': minimum},
            )
        return cleaned_data

    def save(self, commit=True):
        bid = super().save(commit=False)
        bid.listing = self.listing
        bid.bidder = self.bidder
        if commit:
            bid.save()
        return bid


class AutoBidForm(forms.ModelForm):
    class Meta:
        model = AutoBid
        fields = ['max_amount', 'increment']
        widgets = {
            'max_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Maximum auto-bid amount'}),
            'increment': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': 'e.g. 5.00'}),
        }
        labels = {
            'max_amount': 'Max auto-bid amount ($)',
            'increment': 'Bid increment ($)',
        }

    def __init__(self, *args, listing=None, bidder=None, **kwargs):
        self.listing = listing
        self.bidder = bidder
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_max_amount(self):
        amount = self.cleaned_data['max_amount']
        if amount <= 0:
            raise forms.ValidationError('Auto-bid amount must be greater than zero.')
        current = Bid.current_price_for(self.listing)
        if amount <= current:
            raise forms.ValidationError(
                f'Auto-bid must be higher than the current price of ${current}.',
            )
        return amount

    def clean(self):
        cleaned_data = super().clean()
        if self.listing is None:
            return cleaned_data
        if not self.listing.is_active or self.listing.has_ended:
            raise forms.ValidationError('This listing is no longer accepting bids.')
        if self.bidder and self.listing.seller_id == self.bidder.pk:
            raise forms.ValidationError('You cannot auto-bid on your own listing.')
        return cleaned_data

    def clean_increment(self):
        increment = self.cleaned_data['increment']
        if increment <= 0:
            raise forms.ValidationError('Increment must be greater than zero.')
        return increment

    def save(self, commit=True):
        ab, created = AutoBid.objects.update_or_create(
            listing=self.listing,
            bidder=self.bidder,
            defaults={
                'max_amount': self.cleaned_data['max_amount'],
                'increment': self.cleaned_data['increment'],
                'is_active': True,
            },
        )
        return ab
