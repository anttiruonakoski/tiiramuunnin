__doc__ = "Convert tiira.fi CSV file into different formats"
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
    """Muunnetaan ETRSTM-35-FIN tasokoordinaatit maantieteellisiksi koordinaateiksi, päiväys ISO-8601 muotoon ja poistetaan useita kenttiä"""
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
    except IOError as e:
        print("Tallennus epäonnistui.")


if __name__ == "__main__":
    do_conversion = []
    conversions = {
        "maantieteelliset koordinaatit": convert_geographical,
    }

    # argparse ei tosin välitä newlineista,
    epilog = "Mahdolliset muunnokset:\n"
    for k, v in conversions.items():
        epilog += f"{k} : {v.__doc__} \n"
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-f",
        "--in-file",
        type=str,
        help="Input file name (default tiira.csv)",
        dest="filename",
        default="tiira.csv",
    )
    parser.add_argument(
        "-o",
        "--out-file",
        type=str,
        help="Output file name (default tiira_muunnettu.csv)",
        dest="outfilename",
        default="tiira_muunnettu.csv",
    )
    parser.add_argument(
        "-t",
        "--type",
        help="Conversion type (default maantieteelliset koordinaatit)",
        action="append",
        dest="do_conversion",
        default="maantieteelliset koordinaatit",
    )
    args = parser.parse_args()

    if not do_conversion:
        do_conversion.append("maantieteelliset koordinaatit")
    # print(args)
    conversion = do_conversion[0]

    try:
        df, encoding = read_csv(args.filename)
    except IOError as e:
        print(
            f"{args.filename} : virhe tiedoston avaamisessa, tarkista tiedoston sijainti."
        )
        sys.exit(1)

    print(f"Suoritetaan muunnos : {conversion}.")
    result = conversions[conversion](df)
    write_csv(result, args.outfilename, encoding)
    print(f"{args.outfilename} : muunnettu tiedosto valmis.")
