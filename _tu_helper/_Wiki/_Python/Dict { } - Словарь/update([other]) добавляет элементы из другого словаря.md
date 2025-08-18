## update([other]): 

добавляет элементы из другого словаря "other" в текущий словарь. 
# Если ключи из other уже есть в текущем словаре, их значения будут заменены на значения из other.
==================================================
    car = {
    "brand": "Ford",
    "model": "Mustang",
    "year": 1964
    }
    
    car.update({"color": "White"})
    
    print(car) # {'brand': 'Ford', 'model': 'Mustang', 'year': 1964, 'color': 'White'}