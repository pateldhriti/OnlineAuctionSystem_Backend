from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MessageForm
from .models import Conversation


@login_required
def conversation_list(request):
    conversations = (
        Conversation.objects
        .filter(Q(bidder=request.user) | Q(listing__seller=request.user))
        .select_related('listing', 'listing__seller', 'bidder')
        .prefetch_related('messages')
    )
    rows = []
    for conversation in conversations:
        # `.all()` reuses the prefetch cache above; `.last()` on the manager
        # directly would issue a fresh, uncached query per conversation.
        thread = list(conversation.messages.all())
        other_user = (
            conversation.listing.seller
            if request.user.pk == conversation.bidder_id
            else conversation.bidder
        )
        rows.append({
            'conversation': conversation,
            'other_user': other_user,
            'last_message': thread[-1] if thread else None,
        })
    return render(request, 'conversations/conversation_list.html', {'rows': rows})


def _get_conversation_for_participant(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related('listing', 'listing__seller', 'bidder'),
        pk=pk,
    )
    if not conversation.is_participant(request.user):
        raise Http404
    return conversation


@login_required
def conversation_detail(request, pk):
    conversation = _get_conversation_for_participant(request, pk)
    return render(request, 'conversations/conversation_detail.html', {
        'conversation': conversation,
        'messages_thread': conversation.messages.select_related('sender'),
        'form': MessageForm(),
    })


@login_required
@require_POST
def send_message(request, pk):
    conversation = _get_conversation_for_participant(request, pk)
    form = MessageForm(request.POST)
    if form.is_valid():
        message = form.save(commit=False)
        message.conversation = conversation
        message.sender = request.user
        message.save()
        return redirect('conversations:detail', pk=conversation.pk)
    messages.error(request, 'Could not send message.')
    return render(request, 'conversations/conversation_detail.html', {
        'conversation': conversation,
        'messages_thread': conversation.messages.select_related('sender'),
        'form': form,
    })
