class ListingSchema:
    def __init__(self, json_data):
        self.json_data = json_data
        self.loader_data = json_data.get('loaderData', {})
        self.item_recommerce = self.loader_data.get('item-recommerce', {})

    def get_app_config(self):
        return self.loader_data.get('root', {}).get('appConfig', {})

    def get_item_data(self):
        return self.item_recommerce.get('itemData', {})

    def get_meta(self):
        return self.item_recommerce.get('meta', {})

    def get_images(self):
        return self.get_item_data().get('images', [])

    def get_description(self):
        return self.get_item_data().get('description', '')

    def get_category(self):
        return self.get_item_data().get('category', {})

    def extract_all(self):
        return {
            'appConfig': self.get_app_config(),
            'itemData': self.get_item_data(),
            'meta': self.get_meta(),
            'images': self.get_images(),
            'description': self.get_description(),
            'category': self.get_category()
        }
