import os
from db_utils import send_summary_push


def main():
    message = os.environ.get(
        "FULLET_PUSH_MESSAGE",
        "Akaryakit veritabani guncellendi. Uygulamayi yenileyin."
    )
    is_zam = os.environ.get("FULLET_PUSH_IS_ZAM", "0") == "1"
    send_summary_push(message, is_zam=is_zam)


if __name__ == "__main__":
    main()
