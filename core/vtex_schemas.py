from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Optional

class VtexImage(BaseModel):
    imageLabel: Optional[str] = None
    imageTag: Optional[str] = None
    imageUrl: str
    imageText: Optional[str] = None

class VtexInstallment(BaseModel):
    Value: float
    InterestRate: float
    TotalValuePlusInterestRate: float
    NumberOfInstallments: int
    PaymentSystemName: Optional[str] = None

class VtexCommertialOffer(BaseModel):
    Price: float
    ListPrice: float
    PriceWithoutDiscount: float
    RewardValue: float
    PriceValidUntil: Optional[str] = None
    AvailableQuantity: int
    CacheVersion: Optional[str] = None
    Installments: List[VtexInstallment] = []

class VtexSeller(BaseModel):
    sellerId: str
    sellerName: str
    addToCartLink: Optional[str] = None
    sellerDefault: bool
    commertialOffer: VtexCommertialOffer

class VtexItem(BaseModel):
    itemId: str
    name: str
    nameComplete: str
    complementName: Optional[str] = None
    ean: Optional[str] = None
    variations: List[str] = []
    images: List[VtexImage] = []
    sellers: List[VtexSeller] = []

class VtexProduct(BaseModel):
    productId: str
    productName: str
    brand: str
    brandId: int
    linkText: str
    productReference: Optional[str] = None
    categoryId: str
    categories: List[str] = []
    categoriesIds: List[str] = []
    link: str
    description: Optional[str] = None
    items: List[VtexItem] = []
    allSpecifications: List[str] = []
    
    # Campo dinâmico para especificações (ex: "Cor", "Material")
    # A VTEX coloca especificações no nível raiz do objeto
    model_config = {
        "extra": "allow"
    }

    def get_specification(self, name: str) -> Optional[List[str]]:
        """Recupera uma especificação dinâmica por nome."""
        return getattr(self, name, None)
