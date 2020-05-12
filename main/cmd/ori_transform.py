import pandas as pd


def read_excel(file_name, sheet_name):
    df = pd.read_excel(file_name, sheet_name=sheet_name)
    df = df[df[2020] == 'x']
    df = df[['Name', 'Straße', 'Hausnummer']]
    df.columns = ['name', 'street', 'number']
    df['code'] = 71739
    df['city'] = 'Oberriexingen'
    df = df[['code','city','street','number','name']]
    df.to_csv(file_name.replace('xlsx', 'csv'), index=False)


if __name__ == '__main__':
    read_excel('../data/Adressenliste.xlsx', 'Übersicht')
    # main()
