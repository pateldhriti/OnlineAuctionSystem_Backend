from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing

from .models import Conversation, Message


class ConversationModelTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

    def test_is_participant_true_for_bidder_and_seller(self):
        conversation = Conversation.objects.create(listing=self.listing, bidder=self.bidder)

        self.assertTrue(conversation.is_participant(self.bidder))
        self.assertTrue(conversation.is_participant(self.seller))

    def test_is_participant_false_for_stranger(self):
        conversation = Conversation.objects.create(listing=self.listing, bidder=self.bidder)
        stranger = User.objects.create_user(username='stranger', password='pass12345')

        self.assertFalse(conversation.is_participant(stranger))

    def test_only_one_conversation_per_bidder_per_listing(self):
        Conversation.objects.create(listing=self.listing, bidder=self.bidder)

        with self.assertRaises(IntegrityError):
            Conversation.objects.create(listing=self.listing, bidder=self.bidder)


class PlaceBidCreatesConversationTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

    def test_placing_a_bid_creates_a_conversation_with_the_seller(self):
        self.client.force_login(self.bidder)

        self.client.post(reverse('bids:place', args=[self.listing.pk]), {'amount': '30.00'})

        self.assertTrue(
            Conversation.objects.filter(listing=self.listing, bidder=self.bidder).exists()
        )

    def test_a_second_bid_reuses_the_same_conversation(self):
        self.client.force_login(self.bidder)
        self.client.post(reverse('bids:place', args=[self.listing.pk]), {'amount': '30.00'})
        first_conversation = Conversation.objects.get(listing=self.listing, bidder=self.bidder)

        self.client.post(reverse('bids:place', args=[self.listing.pk]), {'amount': '45.00'})

        self.assertEqual(Conversation.objects.filter(listing=self.listing, bidder=self.bidder).count(), 1)
        self.assertEqual(
            Conversation.objects.get(listing=self.listing, bidder=self.bidder).pk,
            first_conversation.pk,
        )

    def test_bid_history_page_links_to_the_conversation_after_bidding(self):
        self.client.force_login(self.bidder)

        response = self.client.post(
            reverse('bids:place', args=[self.listing.pk]), {'amount': '30.00'}, follow=True,
        )

        conversation = Conversation.objects.get(listing=self.listing, bidder=self.bidder)
        self.assertContains(response, reverse('conversations:detail', args=[conversation.pk]))

    def test_bid_history_page_has_no_conversation_link_before_bidding(self):
        response = self.client.get(reverse('bids:history', args=[self.listing.pk]))

        self.assertIsNone(response.context['conversation'])

    def test_bid_history_page_backfills_a_conversation_for_a_pre_existing_bid(self):
        """A Bid placed before the conversation-on-bid trigger existed (or by
        any other means that bypassed place_bid) should still get a working
        "Message seller" link the next time the bid history page loads,
        rather than being permanently missing one.
        """
        from bids.models import Bid

        Bid.objects.create(listing=self.listing, bidder=self.bidder, amount='30.00')
        self.assertFalse(Conversation.objects.filter(listing=self.listing, bidder=self.bidder).exists())
        self.client.force_login(self.bidder)

        response = self.client.get(reverse('bids:history', args=[self.listing.pk]))

        conversation = Conversation.objects.get(listing=self.listing, bidder=self.bidder)
        self.assertEqual(response.context['conversation'], conversation)
        self.assertContains(response, reverse('conversations:detail', args=[conversation.pk]))


class ConversationListViewTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )
        self.conversation = Conversation.objects.create(listing=self.listing, bidder=self.bidder)

    def test_requires_login(self):
        response = self.client.get(reverse('conversations:list'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_bidder_sees_their_conversation(self):
        self.client.force_login(self.bidder)

        response = self.client.get(reverse('conversations:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vintage Clock')

    def test_seller_sees_the_conversation_too(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse('conversations:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bidder')

    def test_unrelated_user_sees_no_conversations(self):
        stranger = User.objects.create_user(username='stranger', password='pass12345')
        self.client.force_login(stranger)

        response = self.client.get(reverse('conversations:list'))

        self.assertNotContains(response, 'Vintage Clock')


class ConversationDetailViewTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')
        self.stranger = User.objects.create_user(username='stranger', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )
        self.conversation = Conversation.objects.create(listing=self.listing, bidder=self.bidder)

    def test_bidder_can_view(self):
        self.client.force_login(self.bidder)

        response = self.client.get(reverse('conversations:detail', args=[self.conversation.pk]))

        self.assertEqual(response.status_code, 200)

    def test_seller_can_view(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse('conversations:detail', args=[self.conversation.pk]))

        self.assertEqual(response.status_code, 200)

    def test_stranger_gets_404(self):
        self.client.force_login(self.stranger)

        response = self.client.get(reverse('conversations:detail', args=[self.conversation.pk]))

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse('conversations:detail', args=[self.conversation.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class SendMessageViewTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')
        self.stranger = User.objects.create_user(username='stranger', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )
        self.conversation = Conversation.objects.create(listing=self.listing, bidder=self.bidder)

    def test_bidder_can_send_a_message(self):
        self.client.force_login(self.bidder)

        response = self.client.post(
            reverse('conversations:send', args=[self.conversation.pk]),
            {'body': 'Is this still available?'},
        )

        self.assertRedirects(response, reverse('conversations:detail', args=[self.conversation.pk]))
        message = Message.objects.get(conversation=self.conversation)
        self.assertEqual(message.sender, self.bidder)
        self.assertEqual(message.body, 'Is this still available?')

    def test_seller_can_reply(self):
        Message.objects.create(conversation=self.conversation, sender=self.bidder, body='Hi!')
        self.client.force_login(self.seller)

        self.client.post(
            reverse('conversations:send', args=[self.conversation.pk]),
            {'body': 'Yes, still available.'},
        )

        self.assertEqual(Message.objects.filter(conversation=self.conversation).count(), 2)
        reply = Message.objects.latest('created_at')
        self.assertEqual(reply.sender, self.seller)

    def test_stranger_cannot_send_a_message(self):
        self.client.force_login(self.stranger)

        response = self.client.post(
            reverse('conversations:send', args=[self.conversation.pk]),
            {'body': 'Sneaky message.'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Message.objects.count(), 0)

    def test_whitespace_only_message_is_rejected(self):
        self.client.force_login(self.bidder)

        response = self.client.post(
            reverse('conversations:send', args=[self.conversation.pk]),
            {'body': '   '},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(Message.objects.count(), 0)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.bidder)

        response = self.client.get(reverse('conversations:send', args=[self.conversation.pk]))

        self.assertEqual(response.status_code, 405)
