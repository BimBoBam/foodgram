import csv

from tqdm import tqdm
from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Import data from csv file into Ingredient model in database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, help='Path to file')

    def handle(self, *args, **options):
        path = (options.get('path')
                or f'{settings.BASE_DIR}/data/ingredients.csv')
        success_count = 0
        self.stdout.write("Loading data...", ending='')
        Ingredient.objects.all().delete()
        self.stdout.write('Database cleared.')
        with open(path, 'r', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            total_lines = sum(1 for _ in open(path, 'r', encoding='utf-8'))
            csv_file.seek(0)

            for row in tqdm(reader, total=total_lines,
                            desc="Importing ingredients"):
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
                        self.stdout.write(f"Invalid row: {row}")
                except IndexError as err:
                    self.stdout.write(f'Error in row {row}: {err}')
        self.stdout.write(f"{success_count} entries were"
                          "imported from .csv file.", ending='')
