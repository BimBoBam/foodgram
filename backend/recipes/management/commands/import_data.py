import csv

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from django.conf import settings
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Import data from csv file into Ingredient model in database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, help='Path to file')

    def handle(self, *args, **options):
        success_count = 0
        self.stdout.write("Loading data...", ending='')
        with open(
                f'{settings.BASE_DIR}/data/ingredients.csv',
                'r',
                encoding='utf-8',
        ) as csv_file:
            reader = csv.reader(csv_file)

            for row in reader:
                name_csv = 0
                unit_csv = 1
                try:
                    obj, created = Ingredient.objects.get_or_create(
                        name=row[name_csv],
                        measurement_unit=row[unit_csv],
                    )
                    if created:
                        success_count += 1
                    if not created:
                        self.stdout.write(f"Ingredient {obj} already" 
                                          "exists in database", ending='')
                except IntegrityError as err:
                    self.stdout.write(f"Error in row {row}:"
                                      f"{err}", ending='')
        self.stdout.write(f"{success_count} entries were"
                          "imported from .csv file.", ending='')
