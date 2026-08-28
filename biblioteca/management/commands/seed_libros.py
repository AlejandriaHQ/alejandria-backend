"""
Comando de seed del catálogo: crea 100 libros reales con portadas por URL.

Usa las portadas de Open Library (servicio público y gratuito) por ISBN:
    https://covers.openlibrary.org/b/isbn/<ISBN>-M.jpg

Idempotente por ISBN: re-ejecutarlo no duplica (update_or_create). Añade
categorías de referencia si no existen. No toca usuarios ni préstamos.

Uso:
    uv run python manage.py seed_libros
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from biblioteca.models import Categoria, Libro

# (titulo, autor, isbn, anio, editorial, cantidad, categoria, descripcion)
LIBROS = [
    # ---------- Clásicos ----------
    ("Cien años de soledad", "Gabriel García Márquez", "9780307474728", 1967, "Vintage Español", 3, "Ficción", "La saga de la familia Buendía en Macondo."),
    ("Don Quijote de la Mancha", "Miguel de Cervantes", "9788420412146", 1605, "Alfaguara", 3, "Clásicos", "Las aventuras del ingenioso hidalgo."),
    ("La Odisea", "Homero", "9780140268867", -800, "Penguin Classics", 2, "Clásicos", "El viaje de regreso de Odiseo a Ítaca."),
    ("La Ilíada", "Homero", "9780140275360", -750, "Penguin Classics", 2, "Clásicos", "El sitio de Troya y la cólera de Aquiles."),
    ("Crimen y castigo", "Fiódor Dostoyevski", "9780143058144", 1866, "Penguin Classics", 2, "Ficción", "Raskólnikov y su crimen."),
    ("Guerra y paz", "León Tolstói", "9781400079988", 1869, "Vintage", 2, "Ficción", "La invasión napoleónica de Rusia."),
    ("Anna Karénina", "León Tolstói", "9780143035008", 1877, "Penguin Classics", 2, "Ficción", "El trágico romance de Anna."),
    ("Los miserables", "Victor Hugo", "9780451419439", 1862, "Signet", 2, "Clásicos", "Jean Valjean y la redención."),
    ("El conde de Montecristo", "Alexandre Dumas", "9780140449266", 1844, "Penguin Classics", 2, "Clásicos", "La venganza de Edmond Dantès."),
    ("Orgullo y prejuicio", "Jane Austen", "9780141439518", 1813, "Penguin Classics", 2, "Clásicos", "Elizabeth Bennet y el señor Darcy."),
    ("Moby Dick", "Herman Melville", "9780142437247", 1851, "Penguin Classics", 2, "Clásicos", "La caza de la ballena blanca."),
    ("Ulises", "James Joyce", "9780141182803", 1922, "Penguin Modern Classics", 2, "Ficción", "Un día en la vida de Leopold Bloom."),
    ("En busca del tiempo perdido", "Marcel Proust", "9780142437964", 1913, "Penguin Classics", 2, "Ficción", "La monumental novela de Proust."),
    ("El Gran Gatsby", "F. Scott Fitzgerald", "9780743273565", 1925, "Scribner", 3, "Ficción", "El sueño americano en los años 20."),
    ("Matar a un ruiseñor", "Harper Lee", "9780060935467", 1960, "Harper Perennial", 3, "Ficción", "La justicia y el racismo en el sur de EE. UU."),
    ("1984", "George Orwell", "9780451524935", 1949, "Signet", 3, "Ficción", "La distopía del Gran Hermano."),
    ("Rebelión en la granja", "George Orwell", "9780451526342", 1945, "Signet", 2, "Ficción", "La alegoría de la revolución."),
    ("El señor de las moscas", "William Golding", "9780399501487", 1954, "Perigee", 2, "Ficción", "Niños varados en una isla."),
    ("El extranjero", "Albert Camus", "9780679720201", 1942, "Vintage", 2, "Ficción", "El absurdo de Meursault."),
    ("La metamorfosis", "Franz Kafka", "9780553213690", 1915, "Bantam", 2, "Ficción", "Gregor Samsa convertido en insecto."),
    ("Cumbres borrascosas", "Emily Brontë", "9780141439556", 1847, "Penguin Classics", 2, "Clásicos", "El amor trágico de Heathcliff."),
    ("Jane Eyre", "Charlotte Brontë", "9780141441146", 1847, "Penguin Classics", 2, "Clásicos", "La institutriz independiente."),
    ("El retrato de Dorian Gray", "Oscar Wilde", "9780141439570", 1890, "Penguin Classics", 2, "Clásicos", "El retrato que envejece."),
    ("Drácula", "Bram Stoker", "9780141439846", 1897, "Penguin Classics", 2, "Clásicos", "La novela gótica del vampiro."),
    ("Frankenstein", "Mary Shelley", "9780141439471", 1818, "Penguin Classics", 2, "Clásicos", "La criatura del doctor Frankenstein."),
    ("El extraño caso del Dr. Jekyll y Mr. Hyde", "Robert Louis Stevenson", "9780141439730", 1886, "Penguin Classics", 2, "Clásicos", "La dualidad del ser humano."),
    ("Tres hermanas", "Antón Chéjov", "9780140444780", 1901, "Penguin Classics", 1, "Clásicos", "Obra de teatro de Chéjov."),
    ("El proceso", "Franz Kafka", "9780805209902", 1925, "Schocken", 2, "Ficción", "Joseph K. y su juicio absurdo."),
    ("Los hermanos Karamázov", "Fiódor Dostoyevski", "9780374528379", 1880, "Farrar Straus Giroux", 2, "Ficción", "El drama de los hermanos Karamázov."),
    ("Madame Bovary", "Gustave Flaubert", "9780140449129", 1856, "Penguin Classics", 2, "Ficción", "Emma Bovary y su insatisfacción."),
    # ---------- Ciencia Ficción y Fantasía ----------
    ("Dune", "Frank Herbert", "9780441013593", 1965, "Ace", 3, "Ciencia Ficción", "La épica de Arrakis y Paul Atreides."),
    ("Fundación", "Isaac Asimov", "9780553293357", 1951, "Bantam", 2, "Ciencia Ficción", "La caída del Imperio Galáctico."),
    ("Yo, robot", "Isaac Asimov", "9780553382563", 1950, "Spectra", 2, "Ciencia Ficción", "Las tres leyes de la robótica."),
    ("El fin de la eternidad", "Isaac Asimov", "9780553291643", 1955, "Bantam", 2, "Ciencia Ficción", "La Eternidad y el cambio temporal."),
    ("2001: Una odisea del espacio", "Arthur C. Clarke", "9780451457998", 1968, "Roc", 2, "Ciencia Ficción", "La odisea de la Humanidad y el monolito."),
    ("Cita con Rama", "Arthur C. Clarke", "9780553287899", 1973, "Spectra", 2, "Ciencia Ficción", "El misterio de Rama."),
    ("Solaris", "Stanislaw Lem", "9780156027601", 1961, "Mariner Books", 2, "Ciencia Ficción", "El océano pensante de Solaris."),
    ("Un mundo feliz", "Aldous Huxley", "9780060850524", 1932, "Harper Perennial", 3, "Ciencia Ficción", "La sociedad perfecta de Huxley."),
    ("Fahrenheit 451", "Ray Bradbury", "9781451673319", 1953, "Simon & Schuster", 3, "Ciencia Ficción", "Los bomberos que queman libros."),
    ("El hombre ilustrado", "Ray Bradbury", "9780553274494", 1951, "Bantam", 2, "Ciencia Ficción", "Relatos de Bradbury."),
    ("Crónicas marcianas", "Ray Bradbury", "9780553278225", 1950, "Bantam", 2, "Ciencia Ficción", "La colonización de Marte."),
    ("El fin de la infancia", "Arthur C. Clarke", "9780345447584", 1953, "Del Rey", 2, "Ciencia Ficción", "Los Señores Supremos y la Tierra."),
    ("Neuromante", "William Gibson", "9780441569595", 1984, "Ace", 2, "Ciencia Ficción", "El ciberpunk fundacional."),
    ("Snow Crash", "Neal Stephenson", "9780553380958", 1992, "Spectra", 2, "Ciencia Ficción", "El metaverso de Hiro Protagonist."),
    ("La mano izquierda de la oscuridad", "Ursula K. Le Guin", "9780441478125", 1969, "Ace", 2, "Ciencia Ficción", "El planeta Invierno."),
    ("Los desposeídos", "Ursula K. Le Guin", "9780061054884", 1974, "Harper Voyager", 2, "Ciencia Ficción", "Anarres y Urras."),
    ("Un mago de Terramar", "Ursula K. Le Guin", "9780547773742", 1968, "HMH Books", 2, "Fantasía", "Ged y la escuela de magia."),
    ("El hobbit", "J. R. R. Tolkien", "9780547928227", 1937, "Houghton Mifflin", 3, "Fantasía", "Bilbo Bolsón y el dragón Smaug."),
    ("La comunidad del anillo", "J. R. R. Tolkien", "9780547928210", 1954, "Houghton Mifflin", 3, "Fantasía", "La primera parte de El Señor de los Anillos."),
    ("Las dos torres", "J. R. R. Tolkien", "9780547928203", 1954, "Houghton Mifflin", 3, "Fantasía", "La segunda parte de El Señor de los Anillos."),
    ("El retorno del rey", "J. R. R. Tolkien", "9780547928197", 1955, "Houghton Mifflin", 3, "Fantasía", "La tercera parte de El Señor de los Anillos."),
    ("Las crónicas de Narnia", "C. S. Lewis", "9780064404990", 1950, "HarperTrophy", 2, "Fantasía", "Las aventuras en Narnia."),
    ("El león, la bruja y el armario", "C. S. Lewis", "9780064404990", 1950, "HarperTrophy", 2, "Fantasía", "El primer viaje a Narnia."),
    ("El nombre del viento", "Patrick Rothfuss", "9780756404741", 2007, "DAW", 2, "Fantasía", "Kvothe y su historia."),
    ("El camino de los reyes", "Brandon Sanderson", "9780765326355", 2010, "Tor Books", 2, "Fantasía", "El primer libro de El Archivo de las Tormentas."),
    ("Elantris", "Brandon Sanderson", "9780765350374", 2005, "Tor Fantasy", 2, "Fantasía", "La ciudad de Elantris."),
    ("Mistborn", "Brandon Sanderson", "9780765350381", 2006, "Tor Fantasy", 2, "Fantasía", "El imperio final y la alomancia."),
    ("Los juegos del hambre", "Suzanne Collins", "9780439023481", 2008, "Scholastic", 3, "Ciencia Ficción", "Katniss Everdeen en Panem."),
    ("Ready Player One", "Ernest Cline", "9780307887443", 2011, "Broadway Books", 2, "Ciencia Ficción", "La búsqueda del huevo de Pascua en OASIS."),
    ("La carretera", "Cormac McCarthy", "9780307387899", 2006, "Vintage", 2, "Ficción", "Padre e hijo en un mundo apocalíptico."),
    # ---------- Ficción contemporánea ----------
    ("El código Da Vinci", "Dan Brown", "9780307474278", 2003, "Anchor", 3, "Misterio", "Robert Langdon y el Santo Grial."),
    ("Ángeles y demonios", "Dan Brown", "9781416524793", 2000, "Pocket Books", 2, "Misterio", "La carrera de Langdon en el Vaticano."),
    ("Inferno", "Dan Brown", "9780804172279", 2013, "Anchor", 2, "Misterio", "Langdon y la Divina Comedia."),
    ("La sombra del viento", "Carlos Ruiz Zafón", "9780143034902", 2001, "Penguin", 2, "Misterio", "El Cementerio de los Libros Olvidados."),
    ("El juego del ángel", "Carlos Ruiz Zafón", "9780061992661", 2008, "Harper", 2, "Misterio", "La continuación de la saga."),
    ("La casa de los espíritus", "Isabel Allende", "9780553383805", 1982, "Bantam", 2, "Ficción", "La saga de la familia Trueba."),
    ("Como agua para chocolate", "Laura Esquivel", "9780385721234", 1989, "Anchor", 2, "Ficción", "El amor y la cocina de Tita."),
    ("El amor en los tiempos del cólera", "Gabriel García Márquez", "9780307387264", 1985, "Vintage", 2, "Ficción", "El amor eterno de Florentino Ariza."),
    ("Crónica de una muerte anunciada", "Gabriel García Márquez", "9781400034957", 1981, "Vintage", 2, "Ficción", "La muerte de Santiago Nasar."),
    ("El otoño del patriarca", "Gabriel García Márquez", "9780307387332", 1975, "Vintage", 2, "Ficción", "El dictador latinoamericano."),
    ("Rayuela", "Julio Cortázar", "9788437604570", 1963, "Cátedra", 2, "Ficción", "La novela que se puede leer en varios órdenes."),
    ("Ficciones", "Jorge Luis Borges", "9788420633295", 1944, "Alianza", 2, "Ficción", "Los cuentos laberínticos de Borges."),
    ("El Aleph", "Jorge Luis Borges", "9788420633226", 1949, "Alianza", 2, "Ficción", "El Aleph y otros cuentos."),
    ("Pedro Páramo", "Juan Rulfo", "9780802133902", 1955, "Grove Press", 2, "Ficción", "El pueblo fantasma de Comala."),
    ("La ciudad y los perros", "Mario Vargas Llosa", "9788490624328", 1963, "Debolsillo", 2, "Ficción", "La vida en el colegio militar."),
    ("La fiesta del chivo", "Mario Vargas Llosa", "9780312424868", 2000, "Picador", 2, "Ficción", "El régimen de Trujillo."),
    ("Conversación en La Catedral", "Mario Vargas Llosa", "9780312424868", 1969, "Picador", 2, "Ficción", "La dictadura de Odría."),
    ("El túnel", "Ernesto Sabato", "9788437608523", 1948, "Cátedra", 2, "Ficción", "La obsesión de Juan Pablo Castel."),
    ("Sobre héroes y tumbas", "Ernesto Sabato", "9788437601708", 1961, "Cátedra", 2, "Ficción", "La novela total de Sabato."),
    ("La tregua", "Mario Benedetti", "9788497593720", 1960, "Punto de Lectura", 2, "Ficción", "El diario de Martín Santomé."),
    ("Memoria del fuego", "Eduardo Galeano", "9788495319077", 1982, "Siglo XXI", 2, "Ficción", "La trilogía sobre América Latina."),
    ("El beso de la mujer araña", "Manuel Puig", "9788497594147", 1976, "Punto de Lectura", 2, "Ficción", "Dos presos en una celda."),
    ("Aura", "Carlos Fuentes", "9788437619918", 1962, "Cátedra", 2, "Ficción", "La novela corta de Fuentes."),
    ("La muerte de Artemio Cruz", "Carlos Fuentes", "9788437617891", 1962, "Cátedra", 2, "Ficción", "El último día de Artemio Cruz."),
    ("Cien años de magia", "Varios", "9788423323551", 1995, "Destino", 1, "Ficción", "Antología de autores hispanoamericanos."),
    ("El principito", "Antoine de Saint-Exupéry", "9780156012195", 1943, "Mariner Books", 3, "Infantil", "La historia del pequeño príncipe."),
    ("Alicia en el país de las maravillas", "Lewis Carroll", "9780141439761", 1865, "Penguin Classics", 2, "Infantil", "Las aventuras de Alicia."),
    ("El viento en los sauces", "Kenneth Grahame", "9780143039099", 1908, "Penguin", 2, "Infantil", "Las aventuras del Sapo y sus amigos."),
    ("Peter Pan", "J. M. Barrie", "9780141322575", 1911, "Puffin", 2, "Infantil", "El niño que no quería crecer."),
    ("Charlie y la fábrica de chocolate", "Roald Dahl", "9780142410318", 1964, "Puffin", 2, "Infantil", "La fábrica de Willy Wonka."),
    ("Matilda", "Roald Dahl", "9780142410370", 1988, "Puffin", 2, "Infantil", "La niña superdotada."),
    # ---------- No ficción ----------
    ("Sapiens: De animales a dioses", "Yuval Noah Harari", "9780062316097", 2011, "Harper", 3, "Historia", "La historia de la humanidad."),
    ("Homo Deus", "Yuval Noah Harari", "9780062464316", 2015, "Harper", 2, "Historia", "El futuro de la humanidad."),
    ("Breve historia del tiempo", "Stephen Hawking", "9780553380163", 1988, "Bantam", 2, "Ciencia", "El universo de Hawking."),
    ("El gen egoísta", "Richard Dawkins", "9780199291151", 1976, "Oxford University Press", 2, "Ciencia", "La evolución desde los genes."),
    ("El origen de las especies", "Charles Darwin", "9780451529060", 1859, "Signet", 2, "Ciencia", "La teoría de la evolución."),
    ("La doble hélice", "James D. Watson", "9780743216301", 1968, "Touchstone", 2, "Ciencia", "El descubrimiento del ADN."),
    ("Una breve historia de casi todo", "Bill Bryson", "9780767908184", 2003, "Broadway Books", 2, "Ciencia", "La ciencia explicada."),
    ("El poder del ahora", "Eckhart Tolle", "9781577314806", 1997, "New World Library", 2, "Autoayuda", "La práctica de la presencia."),
    ("Piense y hágase rico", "Napoleon Hill", "9781585424337", 1937, "TarcherPerigee", 2, "Autoayuda", "Los principios del éxito."),
    ("Cómo ganar amigos e influir sobre las personas", "Dale Carnegie", "9781439167342", 1936, "Simon & Schuster", 2, "Autoayuda", "Las relaciones humanas."),
    ("Meditaciones", "Marco Aurelio", "9780812968255", 180, "Modern Library", 2, "Filosofía", "Los pensamientos del emperador estoico."),
    ("Así habló Zaratustra", "Friedrich Nietzsche", "9780140441185", 1883, "Penguin Classics", 2, "Filosofía", "La filosofía del superhombre."),
    ("El contrato social", "Jean-Jacques Rousseau", "9780140442014", 1762, "Penguin Classics", 2, "Filosofía", "La teoría del contrato social."),
    ("La riqueza de las naciones", "Adam Smith", "9780553585971", 1776, "Bantam Classics", 2, "Historia", "Los fundamentos de la economía."),
    ("El capital", "Karl Marx", "9780140445688", 1867, "Penguin Classics", 2, "Historia", "La crítica de la economía política."),
]


class Command(BaseCommand):
    help = "Crea 100 libros de ejemplo con portadas por URL (idempotente)."

    @transaction.atomic
    def handle(self, *args, **options):
        categorias = {}
        for _, _, _, _, _, _, categoria_nombre, _ in LIBROS:
            categorias[categoria_nombre] = None

        creados = 0
        actualizados = 0
        for (titulo, autor, isbn, anio, editorial, cantidad,
             categoria_nombre, descripcion) in LIBROS:
            cat, _ = Categoria.objects.get_or_create(
                nombre=categoria_nombre,
                defaults={'descripcion': f'Categoría {categoria_nombre}.'},
            )
            portada = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"
            libro, creado = Libro.objects.update_or_create(
                isbn=isbn,
                defaults={
                    'titulo': titulo,
                    'autor': autor,
                    'anio': anio,
                    'editorial': editorial,
                    'descripcion': descripcion,
                    'cantidad': cantidad,
                    'portada': portada,
                    'id_categoria': cat,
                    'activo': True,
                },
            )
            if creado:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Catálogo listo: {creados} libros creados, "
            f"{actualizados} actualizados (total en BD: "
            f"{Libro.objects.count()})."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Categorías: {', '.join(sorted(categorias.keys()))}."
        ))
