from django.conf import settings


def student_footer(request):
    return {
        'student_name': getattr(settings, 'STUDENT_NAME', 'Ricardo Carrasco'),
        'student_section': getattr(settings, 'IEC-N4-C2', 'Programacion Backend'),
        'student_year': getattr(settings, 'STUDENT_YEAR', 2026),
    }