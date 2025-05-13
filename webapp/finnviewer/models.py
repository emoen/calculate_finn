from django.db import models


class Listing(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    data = models.TextField()
    inserted_at = models.DateTimeField()

    class Meta:
        db_table = 'listings'
