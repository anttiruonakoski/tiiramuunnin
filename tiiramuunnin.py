__doc__ = "Convert tiira.fi CSV file into different formats"
__doc_fi__ = (
    "Muuntaa tiira.fi havaintopalvelusta ladatun CSV-tiedoston eri formaatteihin"
)
__author__ = "Antti Ruonakoski"
__copyright__ = "Copyright 2020"
__license__ = "MIT"
__version__ = "1.0"
__maintainer__ = "Antti Ruonakoski"
__email__ = "aruonakoski@gmail.com"


from datetime import datetime, timedelta
import pandas as pd
import argparse
import sys
from pyproj import Transformer

pd.options.mode.chained_assignment = None
float_format = "%.10f"
pd.options.display.float_format = "{:,.10f}".format

default_infile = "tiira.csv"
default_outfile = "tiira_muunnettu.csv"


def finnish_date_converter(date):
    """convert Finnish date format dd.mm.yyyy to ISO-8601"""
    if date:
        return pd.to_datetime(date, format="%d.%m.%Y", errors="coerce")


def read_csv(csv_file="tiira.csv"):
    parse_dates = ["Tallennusaika"]
    for encoding in ["utf-8", "iso-8859-15"]:
        try:
            df = pd.read_csv(
                csv_file,
                sep="#",
                parse_dates=parse_dates,
                keep_default_na=True,
                converters={
                    "Pvm1": finnish_date_converter,
                    "Pvm2": finnish_date_converter,
                },
                encoding=encoding,
            )
            break
        except UnicodeDecodeError:
            # enkoodaus olikin Tiiran default ISO-8859-15. :c uusi yritys.
            pass

    # tiiran muodostamassa csv-tiedostossa 0-havaintojen yksilömäärä kirjoitettu tyhjänä 'Määrä' sarakkeena. täytetään nollat.
    df["Määrä"] = df["Määrä"].fillna(0)
    return df, encoding


def convert_geographical(df: pd.DataFrame):

    """Muuntaa ETRSTM-35-FIN tasokoordinaatit maantieteellisiksi koordinaateiksi ja havainnon alkupäiväyksen ISO-8601 muotoon. Poistaa useita kenttiä. Seuraavat säilytetään:
    "Laji", "Pvm1", "Kunta", "Paikka", "X-koord", "Y-koord", "rivityyppi", "rivejä".
    """

    from_proj = "epsg:3067"  # ETRS-TM35FIN
    to_proj = "epsg:4326"  # WGS-84
    transformer = Transformer.from_crs(from_proj, to_proj)

    selected_fields = [
        "Laji",
        "Pvm1",
        "Kunta",
        "Paikka",
        "X-koord",
        "Y-koord",
        "rivityyppi",
        "rivejä",
    ]
    df = df[selected_fields]

    df["Paikka"] = df[["Kunta", "Paikka"]].apply(lambda x: ", ".join(x), axis=1)
    df = df.drop(["Kunta"], axis=1)
    df[["Y-koord", "X-koord"]] = list(
        df[["X-koord", "Y-koord"]].apply(
            lambda x: transformer.transform(x[0], x[1]), axis=1
        )
    )
    # print(df.head())
    return df


def write_csv(df: pd.DataFrame, filename: str, encoding="utf-8"):
    """Tallennetaan csv-tiedosto. Merkistökoodaus säilytetään."""
    separator = ","
    global float_format
    try:
        df.to_csv(
            filename,
            index=False,
            encoding=encoding,
            sep=separator,
            float_format=float_format,
        )
    except IOError:
        print("Tallennus epäonnistui.")


if __name__ == "__main__":
    do_conversion = []
    conversions = {
        "maantieteelliset_koordinaatit": convert_geographical,
    }

    # argparse ei tosin välitä newlineista,
    epilog = "Mahdolliset muunnokset:\n"
    for k, v in conversions.items():
        epilog += f"{k} : {v.__doc__} \n"
    parser = argparse.ArgumentParser(
        description=__doc_fi__,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-f",
        "--input-file",
        type=str,
        help=f"Lähtötiedoston nimi (oletus: {default_infile})",
        dest="filename",
        metavar="lähtötiedosto",
        default=default_infile,
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        default=default_outfile,
        help=f"Muunnetun tiedoston nimi (oletus: {default_outfile})",
        metavar="muunnettu tiedosto",
        dest="outfilename",
    )
    parser.add_argument(
        "-t",
        "--type",
        metavar="muunnostyyppi",
        help="Muunnostyyppi (oletus maantieteelliset_koordinaatit). \n \
            Voit antaa useita muunnostyyppejä.",
        action="append",
        dest="conversion_types",
        default=[],
    )
    args = parser.parse_args()

    # print(args)
    if not args.conversion_types:
        args.conversion_types.append("maantieteelliset_koordinaatit")

    try:
        df, encoding = read_csv(args.filename)
    except IOError:
        print(
            f"{args.filename} : virhe tiedoston avaamisessa, tarkista tiedoston sijainti."
        )
        sys.exit(1)

    for conversion in args.conversion_types:
        try:
            filename = str(args.outfilename).split(".")
            filename.insert(1, f"_{conversion}.")
            filename = ("").join(filename)
            result = conversions[conversion](df)
            print(f"Suoritetaan muunnos : {conversion}.")
            write_csv(result, filename, encoding)
            print(f"{filename} : muunnettu tiedosto valmis.")
        except KeyError:
            print(f"Virheellinen muunnostyyppi {conversion}.")
       
