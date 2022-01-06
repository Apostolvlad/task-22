import asyncio
import time
from typing import Any, Dict, List

import aiohttp
import requests

import service_file
import timer

#print(requests.get('https://redsale.by/mebel/remont-mebeli/borisov').text.find('У нас больше нет мастеров с параметрами, которые вы задали.'))
#input()
TOKEN = service_file.load_txt('token')

if TOKEN is None or TOKEN == '':
    print('Ошибка, нет токена от redsale, вставьте токен в файл token.txt')
    service_file.save_txt([], 'token', '')
    exit(0)

def request_to_api(url:str, params:dict = {}):
    result =  requests.get(url, params = params)
    result = result.json()
    time.sleep(0.01)
    return result

class City:
    def __init__(self, cityId: int, beautify: str, name: str, **kwarg:dict) -> None:
        self.id = cityId
        self.name = name
        self.beautify = beautify
    
    def __repr__(self) -> str: return f'{self.name} id = {self.id} en = {self.beautify}'

class Container:
    url, type = None, None
    def __init__(self, containerId:int, metro:Any, district:Any, **kwarg:dict) -> None:
        self.id = containerId
        self.metro = metro
        self.district = district
        
    def __repr__(self) -> str: 
        m = f'|metro = {self.metro}' if self.metro else ''
        d = f'|district = {self.district}' if self.district else ''
        return f'id = {self.id}{m}{d}'
    
    @property
    def beautify(self):
        p = self.metro or self.district
        if p:return p["beautify"]
        return False
    
    @property
    def name(self):
        p = self.metro or self.district
        if p:return p["name"]
        return ''
    
    def set_url(self, url) -> str:
        beautify = self.beautify
        if beautify:
            self.url = f'{url}/{beautify}' 
            self.type = 'geo'
        else:
            self.url = url
            self.type = 'main'
        

class Vacancy:
    url = None
    type = 'vacancy'
    name = ''
    def __init__(self, vacancyId:int, seo:dict = None, sectionHeader:str = '', **kwarg:dict) -> None:
        self.id = vacancyId
        if seo: 
            self.header = seo.get('sectionHeader', '')
        else:
            self.header = sectionHeader         

    def __repr__(self) -> str:
        return f'{self.id} {self.header}'
    
    def set_url(self, url) -> str:
        self.url = url.replace('redsale.by/', 'redsale.by/vacancy/')

class Geo:
    def __init__(self, city:City, url:str) -> None:
        self._city:City = city
        self.url:str = f'https://redsale.by/{url}' if self.id == 1 else f'https://{self.beautify}.redsale.by/{url}'
        self.vacancy:Vacancy = None
        self.containers:List[Container] = list()
    
    @property
    def id(self) -> int: return self._city.id

    @property
    def name(self) -> str: return self._city.name

    @property
    def beautify(self) -> str: return self._city.beautify
    
    def add_container(self, container:Container) -> None:
        container.set_url(self.url)
        self.containers.append(container)
    
    def set_vacancy(self, vacancy:Vacancy) -> None:
        vacancy.set_url(self.url)
        self.vacancy = vacancy
    
    def __repr__(self) -> str:
        return f'{self.name}|{self.vacancy}|{self.containers}'

class Section:
    type = ''
    name = ''
    beautify = ''
    specialization = ''
    parent = None
    

    def __init__(self, sectionId:int, **kwarg:dict) -> None:
        self.id:int = sectionId
        self.base_geo:Dict[int, Geo] = dict()
        self.childs:List[Section] = list()
        self.tags:List[str] = list()
        self.update_params(kwarg)

    def update_params(self, kwarg:dict) -> None:
        if kwarg.get('type'): self.type = kwarg['type']
        if kwarg.get('name'): self.name = kwarg['name']
        if kwarg.get('beautify'): self.beautify = kwarg['beautify']
        if kwarg.get('specialization'): self.specialization = kwarg['specialization']
        if kwarg.get('parent'): 
            self.parent = kwarg['parent']
            if not self in self.parent.childs:
                self.parent.childs.append(self)
        for i_tag in range(1, 9):
            tag = kwarg.get(f'tag_{i_tag}')
            if tag is None: break
            self.tags.append(tag) 
        

    def __repr__(self) -> str:
        par = f'|{self.parent}' if self.parent else ''
        return f'Id = {self.id} name = {self.name}{par} url = {self.url}'

    def get_containers(self) -> List[Container]:
        return self.containers
    
    @property
    def url(self) -> str:
        if self.parent:
            if self.type == 'tag_employee':
                return f'{self.parent.url}/tag/{self.beautify}'
            return f'{self.parent.url}/{self.beautify}'
        return self.beautify

    @property
    def parent_id(self) -> int:
        if self.parent: return self.parent.id
        return None
    
    def get_or_create_geo(self, city:City) -> Geo:
        geo = self.base_geo.get(city.id)
        if geo is None:
            geo = Geo(city, self.url)
            self.base_geo.update({geo.id:geo})
        return geo

    def add_container(self, city:City, container:Container) -> None:
        self.get_or_create_geo(city).add_container(container)
    
    def add_vacancy(self, city:City, vacancy:Vacancy) -> None:
        self.get_or_create_geo(city).set_vacancy(vacancy) 

class Sections:
    base:Dict[str, Section] = dict()
    base_urls:Dict[str, Section] = dict()
    white_ids = (24, 6672, 25, 7873, 30, 8890, 32, 9001, 33, 9133, 34,	9229, 36, 9738, 37)
	#(3040, 3042, 3045, 3048, 3049, 6871, 6872, 6873, None)
    @classmethod
    def get_or_create(cls, sectionId:int, parent_default:Any = None, **kwarg:dict) -> Section:
        #if not sectionId in cls.white_ids: return
        if sectionId is None: return
        section = cls.get(sectionId)
        if section is None: 
            section = Section(sectionId = sectionId, parent = cls.get_or_create(sectionId = kwarg.get('parentId', parent_default), parent_default = parent_default), **kwarg)
            cls.base.update({section.id:section})
        elif len(kwarg):
            kwarg.update({'parent':cls.get_or_create(sectionId = kwarg.get('parentId', parent_default))})
            section.update_params(kwarg)
        return section
    
    @classmethod
    def get(cls, id:int) -> Section: return cls.base.get(id)

    @classmethod
    def save(cls):
        with open('data.pickle', 'wb') as f:
            pickle.dump([cls.base, cls.base_urls], f)
    
    @classmethod
    def load(cls):
        with open('data.pickle', 'rb') as f:
            data_new = pickle.load(f)
            cls.base.update(data_new[0])
            cls.base_urls.update(data_new[1])

    @classmethod
    def get_to_url(cls, url:str):
        return cls.base_urls.get(url)

    @classmethod
    def process_distribution(cls):
        for section in cls.base.values():
            cls.base_urls.update({section.url:section})
            continue
            # для добавления geo urls, но нужно отсекать redsale.by/ чтобы получать нужное... да и наверное vacancy тоже не нужно
            for geo in section.base_geo.values():
                for container in geo.containers:
                    cls.base_urls.update({container.url:section})
                vacancy = geo.vacancy
                if vacancy is None: continue
                cls.base_urls.update({vacancy.url:section})
                
@timer.set
def get_cities() -> List[City]:
    params = {'token':TOKEN}
    return [City(**data) for data in request_to_api('https://redsale.by/api/cities', params)] 

@timer.set
def get_root() -> None:
    params = {'token':TOKEN}
    for data in request_to_api('https://redsale.by/api/sections/roots', params):
        if data['sectionId'] in (24, 6672, 25, 7873, 30, 8890, 32, 9001, 33, 9133, 34, 9229, 36, 9738, 37):
            Sections.get_or_create(**data)

@timer.set
def process_root() -> None:
    get_root()
    params = {'token':TOKEN}
    root_ids = tuple(Sections.base.keys())
    for root_id in root_ids:
        b = request_to_api(f'https://redsale.by/api/sections/{root_id}/children', params)
        sec = [Sections.get_or_create(parent_default = root_id, **data) for data in b]
    Sections.process_distribution() # распределяем section по urls
    #print(Sections.get(356))
import pickle


@timer.set
def process_container() -> None:
    cities = get_cities()
    for city in cities:
        params = {'token':TOKEN, 'cityId': city.id}
        for data in request_to_api('https://redsale.by/api/vacancies/sections', params):
            section = Sections.get(data['sectionId'])
            if section is None: continue
            section.add_vacancy(city = city, vacancy = Vacancy(**data)) 

        for data in request_to_api('https://redsale.by/api/containers', params):
            section = Sections.get(data['sectionId'])
            if section is None: continue
            section.add_container(city = city, container = Container(**data))

def get_name_childs(result, child):
    for child in child.childs:
        result.append((child.name, child.type))
        get_name_childs(result, child)

async def fetch_head(session:aiohttp.ClientSession, url):
    async with session.head(url) as response:
        return response.status

@timer.set
async def check_url_status_code():
    async def check(work_queue):
        async with aiohttp.ClientSession() as session:
            while not work_queue.empty():
                geo:Geo = await work_queue.get()
                if geo.vacancy:
                    status_code = await fetch_head(session, geo.vacancy.url)
                    if status_code != 200: 
                        geo.vacancy = None
                for container in tuple(geo.containers):
                    status_code = await fetch_head(session, container.url)
                    if status_code != 200: 
                        geo.containers.remove(container)
                print(work_queue.qsize())
                work_queue.task_done()

    work_queue = asyncio.Queue()
    

    for section in Sections.base.values():
        for geo in section.base_geo.values():
            await work_queue.put(geo)

    await asyncio.gather(
        asyncio.create_task(check(work_queue)),
        asyncio.create_task(check(work_queue)),
        asyncio.create_task(check(work_queue)),
        asyncio.create_task(check(work_queue)),
        asyncio.create_task(check(work_queue))
    )

async def main():
    if True:
        process_root()
        process_container()
        await check_url_status_code()
        Sections.save()
        return 
    Sections.load()
    # https://redsale.by/krasota/narashivanie-nogtei/molodechno
    section =Sections.get_to_url('courses')
    section_child = section.childs
    return 
    result = list()
    print(list(map(lambda x: list(map(lambda y: y.url, x.containers)), Sections.get_to_url('gruzoperevozki/vyivoz-musora').base_geo.values())))
    get_name_childs(result, Sections.get_to_url('artist/animators'))
    print(result)
    print('')

if __name__ == '__main__':
    asyncio.run(main())