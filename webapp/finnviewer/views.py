# finnviewer/views.py
from django.http import JsonResponse
from django.shortcuts import render
from .models import Listing
from django.core.exceptions import ObjectDoesNotExist


def listing_data(request):
    print("Entering listing_data view")  # Debugging: Entry point

    try:
        # Fetch the first available listing
        listing = Listing.objects.first()
        if not listing:
            print("No listings found")  # Debugging: If no listings are found
            return JsonResponse({'error': 'No listings found'}, status=404)

        print("Fetched Listing:", listing)  # Debugging: After fetching data

        # Convert the listing to a dictionary
        listing_data = {
            'id': listing.id,
            'data': listing.data,
            'inserted_at': listing.inserted_at,
        }

    except Exception as e:
        # Debugging: Catch any other exceptions
        print("Error fetching listing:", e)
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse(listing_data, safe=False)


def index(request):
    return render(request, 'index.html')
