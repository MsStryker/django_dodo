from collections import defaultdict

from django.core.management.base import BaseCommand

from django_dodo.models import EmailStats
from django_dodo.views import stats_to_list
from django_dodo.utils import AmazonSES


def stat_factory():
    return {'delivery_attempts': 0,
            'bounces': 0,
            'complaints': 0,
            'rejects': 0}


class Command(BaseCommand):
    """
    Get SES sending statistic and store the result, grouped by date.
    """

    def handle(self, *args, **options):
        connection = AmazonSES().connection

        stats = connection.get_send_statistics()
        data_points = stats_to_list(stats, localize=False)
        stats_dict = defaultdict(stat_factory)

        for data in data_points:
            attempts = int(data['DeliveryAttempts'])
            bounces = int(data['Bounces'])
            complaints = int(data['Complaints'])
            rejects = int(data['Rejects'])
            data_date = data['Timestamp'].split('T')[0]

            stats_dict[data_date]['delivery_attempts'] += attempts
            stats_dict[data_date]['bounces'] += bounces
            stats_dict[data_date]['complaints'] += complaints
            stats_dict[data_date]['rejects'] += rejects

        for key, value in stats_dict.items():
            # stat, created = SESStat.objects.get_or_create(
            stat, created = EmailStats.objects.update_or_create(
                date=key,
                defaults={'delivery_attempts': value['delivery_attempts'],
                          'bounces': value['bounces'],
                          'complaints': value['complaints'],
                          'rejects': value['rejects']}
            )

            # If statistic is not new, modify data if values are different
            # if not created and stat.delivery_attempts != value['delivery_attempts']:
            #     stat.delivery_attempts = value['delivery_attempts']
            #     stat.bounces = value['bounces']
            #     stat.complaints = value['complaints']
            #     stat.rejects = value['rejects']
            #     stat.save()
