export const PRODUCT_TYPES = [
  { value: "fertilized_eggs", label: "البيض المخصب" },
  { value: "day_old_chicks", label: "كتاكيت عمر يوم" },
] as const;

export const BREEDS: Record<string, { value: string; label: string }[]> = {
  fertilized_eggs: [
    { value: "white", label: "أبيض" },
    { value: "sasso", label: "ساسو" },
    { value: "baladi", label: "بلدي" },
    { value: "local", label: "محلي / فيومي وجميزة" },
    { value: "duck", label: "بط" },
    { value: "quail", label: "سمان" },
    { value: "turkey", label: "رومي" },
    { value: "ostrich", label: "نعام" },
    { value: "brown", label: "بني" },
  ],
  day_old_chicks: [
    { value: "white", label: "أبيض" },
    { value: "sasso", label: "ساسو" },
    { value: "baladi", label: "بلدي" },
  ],
};

export const GOVERNORATES = [
  "القاهرة",
  "الإسكندرية",
  "الدقهلية",
  "الشرقية",
  "البحيرة",
  "الغربية",
  "القليوبية",
  "المنوفية",
  "كفر الشيخ",
  "دمياط",
  "بورسعيد",
  "الإسماعيلية",
  "السويس",
  "شمال سيناء",
  "جنوب سيناء",
  "المنيا",
  "أسيوط",
  "سوهاج",
  "قنا",
  "الأقصر",
  "أسوان",
  "الفيوم",
  "بني سويف",
  "الجيزة",
  "مطروح",
  "الوادي الجديد",
  "البحر الأحمر",
];

export const UNITS = [
  { value: "per_1000", label: "للـ 1000" },
  { value: "per_egg", label: "للبيضة الواحدة" },
  { value: "per_kilo", label: "للكيلو" },
];

export const REGION_GROUPS: Record<string, string[]> = {
  "القاهرة الكبرى": ["القاهرة", "الجيزة", "القليوبية"],
  "الإسكندرية": ["الإسكندرية", "مطروح", "البحيرة"],
  "الدلتا": ["الدقهلية", "الشرقية", "الغربية", "المنوفية", "كفر الشيخ", "دمياط"],
  "القناة": ["بورسعيد", "الإسماعيلية", "السويس", "شمال سيناء", "جنوب سيناء"],
  "الصعيد": ["المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان", "الفيوم", "بني سويف"],
  "الوجه البحري": ["الوادي الجديد", "البحر الأحمر"],
};

export const CURRENCY = "EGP";

export const DATA_SOURCES = [
  { name: "وزارة الزراعة", type: "رسمي", update: "أسبوعي", reliability: 95 },
  { name: "الغرفة التجارية", type: "رسمي", update: "شهري", reliability: 90 },
  { name: "بورصة الدواجن", type: "مباشر", update: "يومي", reliability: 85 },
  { name: "شركات التفريخ", type: "خاص", update: "يومي", reliability: 78 },
  { name: "أسواق الأعلاف", type: "ميداني", update: "أسبوعي", reliability: 72 },
];

export const INSIGHT_LEVELS = [
  { minDays: 0, label: "غير متاح", desc: "يوجد عدد قليل من نقاط البيانات. انتظر المزيد." },
  { minDays: 3, label: "رؤى أولية", desc: "رؤى أولية بناءً على البيانات المتاحة", type: "early" as const },
  { minDays: 7, label: "اتجاه قصير المدى", desc: "تحليل الاتجاه العام لأسعار السوق", type: "short" as const },
  { minDays: 30, label: "التوقع الإحصائي", desc: "نموذج ARIMA جاهز للتدريب والتنبؤ", type: "model" as const },
  { minDays: 45, label: "التوقع الموسمي", desc: "نموذج Prophet جاهز للتدريب والتنبؤ الموسمي", type: "model" as const },
  { minDays: 90, label: "التوقع الذكي", desc: "نموذج LSTM جاهز للتدريب والتنبؤ المتقدم", type: "model" as const },
];
