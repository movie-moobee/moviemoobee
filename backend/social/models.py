from django.db import models

class Friendship(models.Model):
    # ERD: friendships.  요청·수락(맞팔), 한 행으로 양방향(F-FRD).
    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        ACCEPTED = "accepted", "accepted"
    requester = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="sent_requests")
    addressee = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="received_requests")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["requester", "addressee"], name="uniq_friendship")]
