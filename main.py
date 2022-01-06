from collections import defaultdict

import requests

import service_table

from api_redsale import *

def main():
    with open('main_table.txt', encoding='UTF-8') as f: main_sh = f.read()
    with open('child_table.txt', encoding='UTF-8') as f: child_sh = f.read()

    Sections.load()

    table = service_table.Table('https://docs.google.com/spreadsheets/d/18QjKqrb0A-veQJGgvFnxjvH-WzCHf8RTrP4K2e5AvN0')
   
    table.select_sheet('tables')
    base_data = defaultdict(list)
    base_names = dict()
    for row in table.load_base_sheet():
        base_names.update({row['sectionId']:row['sectionName']})
        base_data[row['sectionId']].append((row['service'], row['price']))

    sh = main_sh
    base_rows = [['ID', 'content']]
    for section_id, params in base_data.items():
        section_name = base_names[section_id]
        sh = main_sh.replace('sectionName', section_name)
        base_items = list()
        for param in params:
            base_items.append(child_sh.replace('service', param[0]).replace('price', param[1]))
        sh = sh.replace('childs', '\n'.join(base_items))
            
        q = Sections.get(int(section_id))
        if q is None:
            print(section_id, 'section not found!')
        
        for geo in q.base_geo.values():
            for container in geo.containers:
                o = container.district or container.metro
                if o:
                    sh2 = sh.replace('cityName', o['name'])
                else:
                    sh2 = sh.replace('cityName', geo.name)
                base_rows.append([container.id, sh2])
                #continue
                res = requests.patch(f'https://redsale.by/api/containers/{container.id}/seoData?token=6PmWUehjZMugwn8mNxdrVqyG5F3wUmm', json = {'tablePrice':sh2})
                #print(res.text)
                if res.status_code != 200:
                    print(res.text)
                    input()
    table.clear_sheet('заливка')
    table.update_values(base_rows)
    print()

    
    



if __name__ == '__main__':
    main()
