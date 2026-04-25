"""
Site-specific configuration for schema generation.
Contains business details for each managed WordPress site.
"""

SITE_CONFIGS = {
    "e-therm.gr": {
        "business_type": "HVACBusiness",
        "name": "E-Therm",
        "url": "https://e-therm.gr",
        "logo": "https://e-therm.gr/wp-content/uploads/2023/04/logo.png",
        "telephone": "+302109852693",
        "description": "Η E-Therm ειδικεύεται σε συστήματα θέρμανσης, ενεργειακή διαχείριση, μελέτη, εγκατάσταση και συντήρηση συστημάτων φυσικού αερίου και έκδοση πιστοποιητικών στεγανότητας στην Αττική.",
        "address": {
            "streetAddress": "Ελ. Βενιζέλου 62",
            "addressLocality": "Περιστέρι",
            "addressRegion": "Αττική",
            "postalCode": "12132",
            "addressCountry": "GR",
        },
        "geo": {
            "latitude": "38.01605",
            "longitude": "23.68855",
        },
        "opening_hours": [
            {
                "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "opens": "09:00",
                "closes": "18:00",
            },
            {
                "dayOfWeek": "Saturday",
                "opens": "09:00",
                "closes": "14:00",
            },
        ],
        "price_range": "€50 - €500",
        "currencies_accepted": "EUR",
        "payment_accepted": "Cash, Credit Card, Bank Transfer",
        "social_links": [
            "https://www.facebook.com/ETHERM",
        ],
        "contact_languages": ["Greek", "English"],
    },
    "oikonrg.gr": {
        "business_type": "HVACBusiness",
        "name": "OikonRG",
        "url": "https://oikonrg.gr",
        "logo": "https://oikonrg.gr/wp-content/uploads/logo.png",
        "telephone": "+302114018108",
        "description": "Η OikonRG προσφέρει ολοκληρωμένες υπηρεσίες ενεργειακής διαχείρισης, εγκατάστασης και συντήρησης συστημάτων θέρμανσης και φυσικού αερίου στην Αττική.",
        "address": {
            "streetAddress": "Ελ. Βενιζέλου 62",
            "addressLocality": "Περιστέρι",
            "addressRegion": "Αττική",
            "postalCode": "12132",
            "addressCountry": "GR",
        },
        "geo": {
            "latitude": "38.01605",
            "longitude": "23.68855",
        },
        "opening_hours": [
            {
                "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "opens": "09:00",
                "closes": "18:00",
            },
            {
                "dayOfWeek": "Saturday",
                "opens": "09:00",
                "closes": "14:00",
            },
        ],
        "price_range": "€€",
        "currencies_accepted": "EUR",
        "payment_accepted": "Cash, Credit Card, Bank Transfer",
        "social_links": [],
        "contact_languages": ["Greek", "English"],
    },
}

# Areas served - shared between sites
AREAS_SERVED = [
    "Αθήνα",
    "Περιστέρι",
    "Νίκαια",
    "Κηφισιά",
    "Μαρούσι",
    "Χαλάνδρι",
    "Παλαιό Φάληρο",
    "Γλυφάδα",
    "Κέντρο Αθήνας",
    "Βούλα",
    "Ηλιούπολη",
    "Καλλιθέα",
    "Αγία Παρασκευή",
    "Πειραιάς",
    "Γλυκά Νερά",
    "Παλλήνη",
    "Γέρακας",
    "Πεντέλη",
    "Μελίσσια",
    "Βριλήσσια",
    "Ψυχικό",
    "Φιλοθέη",
    "Νέα Ερυθραία",
    "Εκάλη",
    "Βουλιαγμένη",
    "Βάρη",
    "Ελληνικό",
    "Αργυρούπολη",
    "Άλιμος",
    "Νέα Σμύρνη",
    "Αιγάλεω",
    "Χαϊδάρι",
    "Πετρούπολη",
    "Ίλιον",
    "Κορυδαλλός",
    "Χολαργός",
    "Παπάγου",
    "Ζωγράφου",
    "Καισαριανή",
    "Βύρωνας",
    "Δάφνη",
    "Υμηττός",
    "Νέα Ιωνία",
    "Ηράκλειο",
    "Μεταμόρφωση",
    "Πεύκη",
]


def get_site_config(site_url: str | None) -> dict:
    """
    Get configuration for a site by its URL.

    Args:
        site_url: Full URL like "https://e-therm.gr" or just domain "e-therm.gr"

    Returns:
        Site config dict or default config if not found
    """
    if not site_url:
        return SITE_CONFIGS.get("e-therm.gr", {})

    # Extract domain
    domain = site_url.lower().strip()
    if "://" in domain:
        domain = domain.split("://", 1)[1]
    if "/" in domain:
        domain = domain.split("/", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]

    return SITE_CONFIGS.get(domain, SITE_CONFIGS.get("e-therm.gr", {}))
