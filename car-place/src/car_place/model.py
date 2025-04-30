from pydantic import BaseModel, ValidationError
from typing import Optional

class CarEntry(BaseModel):
    id: int
    title: str
    img_url: Optional[str] = None  
    price: int
    post_url: str
    location: Optional[str] = None
    km: Optional[str] = None

data_example = [ 
      {  
        "id": 1,
        "title": "2020 DFSK suv 580",
        "image": "https://scontent.fscl7-1.fna.fbcdn.net/v/t45.5328-4/486874808_1217337746686056_2224464594778732543_n.jpg?stp=c43.0.260.260a_dst-jpg_p261x260_tt6&_nc_cat=110&ccb=1-7&_nc_sid=247b10&_nc_ohc=yl2Hu69P-UgQ7kNvwENSyCt&_nc_oc=AdlpSPNhocVy_OSOcyiCLLI3kNDLHz5o8dCZ75rGI-zvyQhMlL_D2wTTtGLxIgh96Dw&_nc_zt=23&_nc_ht=scontent.fscl7-1.fna&_nc_gid=ST9ZQp6ME47BZNSSyGK9cA&oh=00_AfGf4XpznR9QRmIZ7qTui5p311sJgfV6Qh5isXhwYZSUag&oe=680A253B",
        "price": 8780000,
        "post_url": "/marketplace/item/697273455956920/?ref=category_feed&referral_code=undefined&referral_story_type=listing&tracking=%7B%22qid%22%3A%22-9204398447645231245%22%2C%22mf_story_key%22%3A%229942574042440489%22%2C%22commerce_rank_obj%22%3A%22%7B%5C%22target_id%5C%22%3A9942574042440489%2C%5C%22target_type%5C%22%3A0%2C%5C%22primary_position%5C%22%3A213%2C%5C%22ranking_signature%5C%22%3A835886626171201382%2C%5C%22commerce_channel%5C%22%3A504%2C%5C%22value%5C%22%3A4.1897251846334e-5%2C%5C%22candidate_retrieval_source_map%5C%22%3A%7B%5C%229942574042440489%5C%22%3A302%7D%7D%22%7D&__tn__=!%3AD",
        "location": "Santiago, RM",
        "km": "100mil km" # puede salir distinto a veces hay que manejar este caso
      }
    ]


try:
    car = CarEntry(**data_example[0])  
    print(car)
except ValidationError as e:
    print(e.errors())
