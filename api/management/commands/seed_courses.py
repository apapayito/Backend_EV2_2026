from datetime import date

from django.core.management.base import BaseCommand

from api.models import Area, Course


class Command(BaseCommand):
    help = 'Carga áreas y diez cursos de ejemplo para probar el catálogo y el carro.'

    def handle(self, *args, **options):
        catalog = {
            'Desarrollo Backend': [
                ('Django REST desde cero', 'Construye APIs profesionales con Django REST Framework.', 45000, 12),
                ('PostgreSQL para aplicaciones web', 'Modelado relacional, consultas y rendimiento en PostgreSQL.', 39000, 15),
                ('Arquitectura de servicios web', 'Diseña servicios mantenibles con autenticación, capas y pruebas.', 52000, 10),
            ],
            'Datos e Inteligencia Artificial': [
                ('Python para análisis de datos', 'Limpia, explora y comunica datos con Python.', 42000, 18),
                ('Fundamentos de Machine Learning', 'Entrena y evalúa modelos predictivos con proyectos guiados.', 59000, 12),
                ('SQL para analistas', 'Domina joins, agregaciones y consultas para tomar decisiones.', 35000, 20),
            ],
            'Desarrollo Frontend': [
                ('Interfaces modernas con Bootstrap', 'Crea interfaces responsive, accesibles y consistentes.', 32000, 20),
                ('JavaScript práctico', 'Interactividad, consumo de APIs y patrones del navegador.', 48000, 14),
                ('React para productos digitales', 'Componentes, estado y flujos de usuario con React.', 56000, 12),
            ],
            'Gestión Tecnológica': [
                ('Agilidad para equipos de software', 'Organiza proyectos tecnológicos con foco en entrega continua.', 36000, 16),
            ],
        }
        start_dates = [date(2026, 10, 5), date(2026, 10, 19), date(2026, 11, 2), date(2026, 11, 16)]
        created = 0
        for area_name, courses in catalog.items():
            area, _ = Area.objects.get_or_create(name=area_name, defaults={'description': f'Ruta de {area_name.lower()}.'})
            for index, (title, description, price, capacity) in enumerate(courses):
                course, was_created = Course.objects.get_or_create(
                    title=title,
                    defaults={
                        'area': area,
                        'description': description,
                        'price': price,
                        'start_date': start_dates[index % len(start_dates)],
                        'end_date': date(2026, 12, 18),
                        'capacity': capacity,
                        'available_seats': capacity,
                    },
                )
                created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f'Catálogo listo: {Course.objects.count()} cursos disponibles ({created} nuevos).'))