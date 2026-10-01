import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Chat, Follow, Message, Profile


class FollowAndChatFlowTests(TestCase):
    def setUp(self):
        self.follower = User.objects.create_user(username='follower', password='test-password')
        self.followed = User.objects.create_user(username='followed', password='test-password')
        self.follower_profile = Profile.objects.create(user=self.follower)
        self.followed_profile = Profile.objects.create(user=self.followed)

        self.chat = Chat.objects.create()
        self.chat.participants.add(self.follower, self.followed)

    def test_follow_totals_use_follow_records(self):
        Follow.objects.create(follower=self.follower, following=self.followed)

        self.assertEqual(self.followed_profile.total_followers(), 1)
        self.assertEqual(self.follower_profile.total_following(), 1)

    def test_follow_and_unfollow_actions_update_totals(self):
        self.client.force_login(self.follower)

        self.client.get(reverse('feed:follow_user', args=[self.followed.username]))
        self.assertEqual(self.followed_profile.total_followers(), 1)
        self.assertEqual(self.follower_profile.total_following(), 1)

        self.client.get(reverse('feed:unfollow_user', args=[self.followed.username]))
        self.assertEqual(self.followed_profile.total_followers(), 0)
        self.assertEqual(self.follower_profile.total_following(), 0)

    def test_search_shows_follow_state_from_follow_records(self):
        Follow.objects.create(follower=self.follower, following=self.followed)
        self.client.force_login(self.follower)

        response = self.client.get(reverse('feed:search_users'), {'q': self.followed.username})

        self.assertContains(response, 'Following')

    def test_chat_list_renders_unread_count(self):
        Message.objects.create(chat=self.chat, sender=self.followed, text='Hello')
        self.client.force_login(self.follower)

        response = self.client.get(reverse('feed:chat_list'))

        self.assertContains(response, 'class="unread-count"')
        self.assertContains(response, '>1</span>')
        self.assertContains(response, 'id="conversationSearch"')
        self.assertContains(response, 'class="conversation-row"')

    def test_opening_chat_marks_incoming_messages_read(self):
        message = Message.objects.create(chat=self.chat, sender=self.followed, text='Hello')
        self.client.force_login(self.follower)

        response = self.client.get(reverse('feed:chat_detail', args=[self.chat.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="premium-card chat-thread-card"')
        self.assertContains(response, 'class="message-composer"')
        self.assertContains(response, 'id="imageUpload"')
        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_chat_accepts_image_without_text(self):
        self.client.force_login(self.follower)
        upload = SimpleUploadedFile('photo.jpg', b'image data', content_type='image/jpeg')
        chat_url = reverse('feed:chat_detail', args=[self.chat.id])

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(chat_url, {'text': '', 'image': upload})

        self.assertRedirects(response, chat_url)
        self.assertTrue(Message.objects.filter(chat=self.chat, sender=self.follower, image__isnull=False).exists())

    def test_mobile_navigation_is_shared_across_authenticated_pages(self):
        self.client.force_login(self.follower)

        for url in (reverse('feed:feed'), reverse('feed:chat_list')):
            response = self.client.get(url)

            self.assertContains(response, 'class="mobile-bottom-nav"')
            self.assertEqual(response.content.decode().count('aria-label="Mobile navigation"'), 1)
            self.assertEqual(response.content.decode().count('aria-current="page"'), 1)
            for label in ('Home', 'Search', 'Upload', 'Messages', 'Profile'):
                self.assertContains(response, f'aria-label="{label}"')

    def test_profile_pages_render_responsive_profile_hero(self):
        self.client.force_login(self.follower)

        for url in (reverse('feed:profile'), reverse('feed:user_profile', args=[self.followed.username])):
            response = self.client.get(url)

            self.assertContains(response, 'class="premium-card profile-hero mb-4"')
            self.assertContains(response, 'class="profile-stats"')
            self.assertContains(response, 'class="profile-bio empty"')

    def test_visitor_profile_has_equal_follow_and_message_actions(self):
        self.client.force_login(self.follower)

        response = self.client.get(reverse('feed:user_profile', args=[self.followed.username]))

        self.assertContains(response, 'class="profile-actions visitor-profile-actions"')
        self.assertContains(response, 'class="btn profile-wide-action" aria-label="Follow followed"')
        self.assertContains(response, 'class="btn profile-wide-action">')

        Follow.objects.create(follower=self.follower, following=self.followed)
        response = self.client.get(reverse('feed:user_profile', args=[self.followed.username]))
        self.assertContains(response, 'aria-label="Unfollow followed"')

    def test_theme_and_logout_controls_are_on_owner_profile(self):
        self.client.force_login(self.follower)

        owner_response = self.client.get(reverse('feed:profile'))
        owner_html = owner_response.content.decode()
        desktop_nav = owner_html.split('<nav class="navbar navbar-expand-lg navbar-dark desktop-navbar">', 1)[1].split('</nav>', 1)[0]

        self.assertContains(owner_response, 'id="themeToggle"')
        self.assertContains(owner_response, 'action="/logout/"')
        self.assertNotIn('themeToggle', desktop_nav)
        self.assertNotIn('/logout/', desktop_nav)

        visitor_response = self.client.get(reverse('feed:user_profile', args=[self.followed.username]))
        self.assertNotContains(visitor_response, 'id="themeToggle"')
        self.assertNotContains(visitor_response, 'action="/logout/"')

    def test_create_post_page_renders_photo_picker_and_caption_editor(self):
        self.client.force_login(self.follower)

        response = self.client.get(reverse('feed:create_post'))

        self.assertContains(response, 'class="premium-card post-composer"')
        self.assertContains(response, 'id="id_image"')
        self.assertContains(response, 'id="imagePreview"')
        self.assertContains(response, 'id="id_caption"')
        self.assertContains(response, 'Share post')