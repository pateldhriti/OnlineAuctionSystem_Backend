from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ContactForm


def home(request):
    return render(request, 'pages/home.html', {'contact_form': ContactForm()})


@require_POST
def contact_submit(request):
    form = ContactForm(request.POST)
    if form.is_valid():
        try:
            send_mail(
                subject=f"New contact message from {form.cleaned_data['name']}",
                message=(
                    f"From: {form.cleaned_data['name']} <{form.cleaned_data['email']}>\n\n"
                    f"{form.cleaned_data['message']}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=True,
            )
        except Exception:
            pass
        messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
        return redirect(reverse('home') + '#contact')

    messages.error(request, 'Please fix the errors below and try again.')
    return render(request, 'pages/home.html', {'contact_form': form})
