import datetime


def year(request):
    return {
        'current_year': datetime.datetime.now().year
    }
