/**
 * Verification functions for additional validation after regex matching.
 * This module provides additional validation beyond regex matching.
 * All verification functions follow the signature: (value: string) => boolean
 */

// --- Data Cache for Heuristics and Custom Data ---
const _DATA_CACHE = new Map();

/**
 * Load values from a data source.
 */
function _loadData(filename) {
  return _DATA_CACHE.get(filename) || new Set();
}

/**
 * Set custom data for a specific filename.
 */
function setCustomData(filename, values) {
  _DATA_CACHE.set(filename, new Set(values));
}

// --- Constants ---

const CHINESE_SURNAMES = new Set([
  "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "吴", "周", "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "高", "罗", "郑", "梁", "谢", "宋", "唐", "许", "邓", "冯", "韩", "曹", "曾", "彭", "萧", "蔡", "潘", "田", "董", "袁", "于", "余", "叶", "蒋", "杜", "苏", "魏", "程", "吕", "丁", "沈", "任", "姚", "卢", "傅", "钟", "姜", "崔", "谭", "廖", "范", "汪", "陆", "金", "石", "戴", "贾", "韦", "夏", "邱", "方", "侯", "邹", "熊", "孟", "秦", "白", "江", "阎", "薛", "尹", "段", "雷", "黎", "史", "龙", "陶", "贺", "顾", "毛", "郝", "龚", "邵", "万", "钱", "严", "赖", "覃", "洪", "武", "莫", "孔",
  "張", "劉", "陳", "楊", "黃", "趙", "吳", "許", "鄭", "謝", "鄧", "馮", "韓", "蕭", "葉", "蔣", "蘇", "魏", "呂", "瀋", "盧", "傅", "鐘", "薑", "譚", "廖", "範", "陸", "賈", "鄒", "閻", "龍", "陶", "賀", "顧", "郝", "龔", "萬", "錢", "嚴", "賴", "覃",
  "欧阳", "歐陽", "司马", "司馬", "上官", "诸葛", "諸葛", "东方", "東方", "皇甫", "尉迟", "尉遲", "公孙", "公孫", "令狐", "慕容", "轩辕", "軒轅", "夏侯", "司徒", "独孤", "獨孤"
]);

const KOREAN_SURNAMES = new Set([
  "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권", "황", "안", "송", "류", "유", "홍", "전", "고", "문", "양", "손", "배", "백", "허", "남", "심", "노", "하", "곽", "성", "차", "주", "우", "구", "민", "진", "나", "지", "엄", "변", "채", "원", "천", "방", "공", "현", "함", "염", "여", "추", "도", "소", "석", "선", "설", "마", "길", "연", "위", "표", "명", "기", "반", "왕", "금", "옥", "육", "인", "맹", "제", "모", "탁", "국", "어", "은", "편", "용", "예", "경", "봉", "사", "부", "황보", "남궁", "독고", "사공", "제갈", "선우"
]);

const JAPANESE_SURNAMES = new Set([
  "佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤", "吉田", "山田", "佐々木", "山口", "松本", "井上", "木村", "林", "斎藤", "清水", "山崎", "森", "阿部", "池田", "橋本", "山下", "石川", "中島", "前田", "藤田", "小川", "後藤", "岡田", "長谷川", "村上", "近藤", "石井", "斉藤", "坂本", "遠藤", "青木", "藤井", "西村", "福田", "太田", "三浦", "藤原", "岡本", "松田", "中川",
  "原田", "小野", "竹内", "金子", "和田", "中野", "原", "田村", "安藤", "河野", "上田", "大野", "高木", "工藤", "内田", "丸山", "今井", "酒井", "宮崎", "横山", "関", "堀", "島", "谷", "浜", "沢", "杉"
]);

const CHINESE_NON_NAME_KEYWORDS = new Set([
  "王国", "王朝", "王牌", "王者", "李子", "张开", "张力", "张贴", "黄金", "黄色", "黄油", "黄土", "黄瓜", "黄河", "黄昏", "高度", "高级", "高中", "高速", "高考", "高峰", "高手", "高端", "周围", "周期", "周末", "周年", "周边", "周到", "马上", "马路", "马力", "朱红", "曹操", "白色", "白天", "白云", "白金", "白菜", "金属", "金融", "金额", "金钱", "金牌", "田地", "田野", "田园", "石头", "石油", "石材", "方法", "方案", "方向", "方式", "方面", "方便", "任务", "任何", "任意", "任命", "程度", "程序", "江山", "江南", "江河", "余额", "余下", "于是", "何时", "何处", "何必",
  "电话", "電話", "邮箱", "郵箱", "地址", "姓名", "信息", "資訊", "联系", "聯繫", "手机", "手機", "号码", "號碼", "传真", "傳真", "邮件", "郵件", "密码", "密碼", "账号", "帳號", "注册", "註冊", "登录", "登錄", "确认", "確認", "验证", "驗證", "性别", "性別", "生日", "职业", "職業", "公司", "部门", "部門", "任务", "任務"
]);

const KOREAN_NON_NAME_KEYWORDS = new Set([
  "전화번호", "이메일", "연락처", "주소", "이름", "성명", "휴대폰", "핸드폰", "번호", "전화", "메일", "팩스", "모바일", "정보", "문의", "확인", "성별", "생년", "월일", "생일", "직업", "나이", "회사", "부서", "직책", "전화번", "메일주", "이메일주", "연락처는", "주소는", "이름은", "성명은"
]);

const JAPANESE_NON_NAME_KEYWORDS = new Set([
  "田園", "田畑", "田舎", "中心", "中央", "中間", "中古", "中止", "中国", "中学", "山脈", "山岳", "山林", "山地", "山頂", "高速", "高校", "高層", "高価", "高原", "高齢", "林業", "林道", "森林", "石油", "石材", "石炭", "石器", "金属", "金融", "金額", "金銭", "金庫", "上記", "上昇", "上手", "上司", "大学", "大会", "大臣", "大量", "大型", "大切", "大変", "小学", "小説", "小型", "小売", "原因", "原則", "原料", "原発", "内容", "内部", "内閣", "前回", "前者", "前提", "前日", "後半", "後者", "後日", "西洋", "西側", "青年", "青春", "近代", "近年", "近所", "遠方", "遠足", "池袋",
  "電話", "住所", "名前", "情報", "連絡", "番号", "携帯", "確認", "登録", "氏名", "性別", "生年", "職業", "会社", "部署", "郵便", "暗号", "認証", "口座"
]);

const ENGLISH_SURNAMES = new Set([
  "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
  "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
  "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
  "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
  "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
  "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
  "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner",
  "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris",
  "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper",
  "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward",
  "Richardson", "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray",
  "Mendoza", "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel",
  "Myers", "Long", "Ross", "Foster", "Jimenez"
]);

// --- Core Verification Functions ---

function iban_mod97(value) {
  const iban = value.replace(/\s/g, "").toUpperCase();
  if (iban.length < 5) return false;
  const rearranged = iban.slice(4) + iban.slice(0, 4);

  let numericString = "";
  for (let i = 0; i < rearranged.length; i++) {
    const char = rearranged[i];
    if (/[0-9]/.test(char)) {
      numericString += char;
    } else if (/[A-Z]/.test(char)) {
      numericString += (char.charCodeAt(0) - "A".charCodeAt(0) + 10).toString();
    } else {
      return false;
    }
  }

  let remainder = 0;
  for (let i = 0; i < numericString.length; i++) {
    remainder = (remainder * 10 + parseInt(numericString[i], 10)) % 97;
  }
  return remainder === 1;
}

function luhn(value) {
  const digits = value.replace(/\D/g, "").split("").map(Number);
  if (digits.length === 0) return false;

  let checksum = 0;
  const reversedDigits = digits.reverse();

  for (let i = 0; i < reversedDigits.length; i++) {
    let digit = reversedDigits[i];
    if (i % 2 === 1) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    checksum += digit;
  }
  return checksum % 10 === 0;
}

function dms_coordinate(value) {
  const pattern = /^(\d{1,3})°\s*(\d{1,2})′\s*(\d{1,2}(?:\.\d+)?)″\s*([NSEW])$/i;
  const match = value.match(pattern);
  if (!match) return false;

  const degrees = parseInt(match[1], 10);
  const minutes = parseInt(match[2], 10);
  const seconds = parseFloat(match[3]);
  const direction = match[4].toUpperCase();

  if (minutes > 59 || seconds >= 60) return false;

  if (direction === "N" || direction === "S") {
    if (degrees > 90) return false;
  } else if (direction === "E" || direction === "W") {
    if (degrees > 180) return false;
  }
  return true;
}

function high_entropy_token(value) {
  if (value.length < 20) return false;
  if (/\s/.test(value)) return false;

  const allowedChars = /^[A-Za-z0-9_\-+/./=]+$/;
  if (!allowedChars.test(value)) return false;

  // Normalize separators to spaces before entropy calculation
  const normalized = value.replace(/[-_|]/g, " ");

  const charCounts = {};
  for (const char of normalized) {
    charCounts[char] = (charCounts[char] || 0) + 1;
  }

  const length = normalized.length;
  let entropy = 0;
  for (const count of Object.values(charCounts)) {
    const p = count / length;
    entropy -= p * Math.log2(p);
  }

  return entropy >= 4.5;
}

function not_timestamp(value) {
  const digitsOnly = value.replace(/\D/g, "");
  if (!digitsOnly) return true;

  const length = digitsOnly.length;
  if (length === 10) {
    const num = parseInt(digitsOnly, 10);
    if (num >= 1000000000 && num <= 9999999999) return false;
  }
  if (length === 13) {
    const num = parseInt(digitsOnly, 10);
    if (num >= 1000000000000 && num <= 9999999999999) return false;
  }
  if (length === 14) {
    const year = parseInt(digitsOnly.slice(0, 4), 10);
    const month = parseInt(digitsOnly.slice(4, 6), 10);
    const day = parseInt(digitsOnly.slice(6, 8), 10);
    const hour = parseInt(digitsOnly.slice(8, 10), 10);
    const minute = parseInt(digitsOnly.slice(10, 12), 10);
    const second = parseInt(digitsOnly.slice(12, 14), 10);

    if (
      year >= 1900 && year <= 2099 &&
      month >= 1 && month <= 12 &&
      day >= 1 && day <= 31 &&
      hour >= 0 && hour <= 23 &&
      minute >= 0 && minute <= 59 &&
      second >= 0 && second <= 59
    ) {
      return false;
    }
  }
  return true;
}

function korean_bank_account_valid(value) {
  const digitsOnly = value.replace(/\D/g, "");
  if (!digitsOnly) return false;
  const knownPrefixes = ["110", "120", "150", "190", "830", "1002", "301", "3333", "100"];
  if (knownPrefixes.some(p => digitsOnly.startsWith(p))) return true;
  if (digitsOnly.length === 10) {
    const num = parseInt(digitsOnly, 10);
    if (num >= 1000000000 && num <= 9999999999) return false;
  }
  return true;
}

function generic_number_not_timestamp(value) {
  const digitsOnly = value.replace(/\D/g, "");
  if (!digitsOnly) return true;
  if (digitsOnly.length === 10) {
    const num = parseInt(digitsOnly, 10);
    if (num >= 1000000000 && num <= 9999999999) return false;
  }
  return true;
}

function contains_letter(value) {
  return /\p{L}/u.test(value);
}

function us_ssn_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 9) return false;
  const area = parseInt(digits.slice(0, 3), 10);
  const group = parseInt(digits.slice(3, 5), 10);
  const serial = parseInt(digits.slice(5, 9), 10);
  if (area === 0 || area === 666 || area >= 900 || group === 0 || serial === 0) return false;
  return true;
}

function chinese_name_valid(value) {
  if (!value || value.length < 2 || value.length > 4) return false;
  if (CHINESE_NON_NAME_KEYWORDS.has(value)) return false;
  let surname = null;
  if (value.length >= 3 && CHINESE_SURNAMES.has(value.slice(0, 2))) surname = value.slice(0, 2);
  else if (CHINESE_SURNAMES.has(value[0])) surname = value[0];
  return surname !== null;
}

function korean_name_valid(value) {
  if (!value || value.length < 2 || value.length > 5) return false;
  if (KOREAN_NON_NAME_KEYWORDS.has(value)) return false;
  let surname = null;
  if (value.length >= 3 && KOREAN_SURNAMES.has(value.slice(0, 2))) surname = value.slice(0, 2);
  else if (KOREAN_SURNAMES.has(value[0])) surname = value[0];
  return surname !== null;
}

function japanese_name_kanji_valid(value) {
  if (!value || value.length < 2 || value.length > 6) return false;
  if (JAPANESE_NON_NAME_KEYWORDS.has(value)) return false;
  let surname = null;
  if (value.length >= 4 && JAPANESE_SURNAMES.has(value.slice(0, 3))) surname = value.slice(0, 3);
  else if (value.length >= 2 && JAPANESE_SURNAMES.has(value.slice(0, 2))) surname = value.slice(0, 2);
  else if (JAPANESE_SURNAMES.has(value[0])) surname = value[0];
  return surname !== null;
}

function cjk_name_standalone(value) {
  if (!value || value.length > 6) return false;
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    if (!((code >= 0x4E00 && code <= 0x9FFF) || (code >= 0xAC00 && code <= 0xD7AF) || (code >= 0x3040 && code <= 0x309F) || (code >= 0x30A0 && code <= 0x30FF))) return false;
  }
  return true;
}

function cn_national_id_valid(value) {
  const idStr = value.replace(/\s/g, "").toUpperCase();
  if (idStr.length !== 18) return false;
  const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
  const checkDigits = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"];
  let total = 0;
  for (let i = 0; i < 17; i++) total += parseInt(idStr[i], 10) * weights[i];
  return idStr[17] === checkDigits[total % 11];
}

function tw_national_id_valid(value) {
  const idStr = value.replace(/\s/g, "").toUpperCase();
  if (idStr.length !== 10 || !/^[A-Z]/.test(idStr) || !/^\d{9}/.test(idStr.slice(1))) return false;
  const mapping = {
    "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15, "G": 16, "H": 17,
    "I": 34, "J": 18, "K": 19, "L": 20, "M": 21, "N": 22, "O": 35, "P": 23,
    "Q": 24, "R": 25, "S": 26, "T": 27, "U": 28, "V": 29, "W": 32, "X": 30,
    "Y": 31, "Z": 33
  };
  const letterCode = mapping[idStr[0]];
  if (!letterCode) return false;
  let total = Math.floor(letterCode / 10) * 1 + (letterCode % 10) * 9;
  const weights = [8, 7, 6, 5, 4, 3, 2, 1];
  for (let i = 0; i < 8; i++) total += parseInt(idStr[i + 1], 10) * weights[i];
  total += parseInt(idStr[9], 10);
  return total % 10 === 0;
}

function kr_rrn_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 13) return false;
  const weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5];
  let total = 0;
  for (let i = 0; i < 12; i++) total += parseInt(digits[i], 10) * weights[i];
  return parseInt(digits[12], 10) === (11 - (total % 11)) % 10;
}

function kr_alien_registration_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 13) return false;
  const weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5];
  let total = 0;
  for (let i = 0; i < 12; i++) total += parseInt(digits[i], 10) * weights[i];
  const checkDigit = (11 - (total % 11)) % 10;
  return parseInt(digits[12], 10) === (checkDigit + 2) % 10;
}

function kr_corporate_registration_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 13) return false;
  const weights = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2];
  let total = 0;
  for (let i = 0; i < 12; i++) total += parseInt(digits[i], 10) * weights[i];
  return parseInt(digits[12], 10) === (10 - (total % 10)) % 10;
}

function jp_driver_license_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 12) return false;
  const weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  let total = 0;
  for (let i = 0; i < 10; i++) total += parseInt(digits[i], 10) * weights[i];
  const remainder = total % 11;
  const expected = remainder <= 1 ? 0 : 11 - remainder;
  return parseInt(digits[10], 10) === expected;
}

function imei_valid(value) {
  const digits = value.replace(/\D/g, "");
  return digits.length === 15 && luhn(digits);
}

function mac_address_valid(value) {
  const mac = value.replace(/[:-\s]/g, "").toUpperCase();
  return mac.length === 12 && mac !== "FFFFFFFFFFFF" && mac !== "000000000000";
}

function ipv4_public(value) {
  const parts = value.split(".");
  if (parts.length !== 4) return false;
  const octets = parts.map(p => parseInt(p, 10));
  if (octets.some(o => isNaN(o) || o < 0 || o > 255)) return false;
  const [f, s, t] = octets;
  if (f === 0 || f === 10 || f === 127) return false;
  if (f === 169 && s === 254) return false;
  if (f === 172 && s >= 16 && s <= 31) return false;
  if (f === 192 && s === 168) return false;
  if (f >= 224) return false;
  return true;
}

function not_repeating_pattern(value) {
  if (!value) return true;
  const normalized = value.replace(/\D/g, "") || value;
  if (new Set(normalized).size === 1) return false;
  if (normalized.length < 4) return true;
  if (/^\d+$/.test(normalized)) {
    let asc = true, desc = true;
    for (let i = 1; i < normalized.length; i++) {
      if (parseInt(normalized[i]) !== parseInt(normalized[i-1]) + 1) asc = false;
      if (parseInt(normalized[i]) !== parseInt(normalized[i-1]) - 1) desc = false;
    }
    if (asc || desc) return false;
  }
  return true;
}

function credit_card_bin_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length < 13 || digits.length > 19) return false;
  return luhn(digits);
}

function english_name_valid(value) {
  const parts = value.trim().split(/\s+/);
  if (parts.length < 2 || parts.length > 4) return false;
  if (!parts.every(p => p.length > 0 && p[0] === p[0].toUpperCase())) return false;

  const firstName = parts[0];
  const lastName = parts[parts.length - 1];

  const validSurnames = _loadData("en_surnames.csv").size > 0 ? _loadData("en_surnames.csv") : ENGLISH_SURNAMES;
  const validGivenNames = _loadData("en_given_names.csv");
  const isCommonGiven = validGivenNames.size > 0 && validGivenNames.has(firstName);
  const isCommonSurname = validSurnames.has(lastName);

  if (isCommonGiven && isCommonSurname) return true;
  if ((isCommonGiven || isCommonSurname) && lastName.length >= 2 && lastName.length <= 15) return true;

  if (parts.length === 2 && /^[A-Za-z]+$/.test(firstName) && /^[A-Za-z]+$/.test(lastName)) {
    if (firstName.length >= 2 && lastName.length >= 2) return true;
  }
  return false;
}

function korean_address_valid(value) {
  const provinces = [
    "서울특별시", "경기도", "부산광역시", "인천광역시", "대구광역시", "대전광역시",
    "광주광역시", "울산광역시", "세종특별자치시", "강원도", "충청북도", "충청남도",
    "전라북도", "전라남도", "경상북도", "경상남도", "제주특별자치도"
  ];
  return provinces.some(p => value.includes(p));
}

function japanese_address_valid(value) {
  const prefectures = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
  ];
  return prefectures.some(p => value.includes(p));
}

function chinese_address_valid(value) {
  const provinces = [
    "北京市", "天津市", "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省",
    "黑龙江省", "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省",
    "山东省", "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
    "重庆市", "四川省", "贵州省", "云南省", "西藏自治区", "陕西省", "甘肃省",
    "青海省", "宁夏回族自治区", "新疆维吾尔自治区", "香港特别行政区", "澳门特别行政区", "台湾省"
  ];
  return provinces.some(p => value.includes(p));
}

const VERIFICATION_FUNCTIONS = {
  iban_mod97, luhn, dms_coordinate, high_entropy_token, not_timestamp,
  korean_bank_account_valid, generic_number_not_timestamp, contains_letter, us_ssn_valid,
  chinese_name_valid, korean_name_valid, japanese_name_kanji_valid, cjk_name_standalone,
  cn_national_id_valid, tw_national_id_valid, india_aadhaar_valid, india_pan_valid,
  kr_business_registration_valid, kr_rrn_valid, kr_alien_registration_valid, jp_my_number_valid,
  kr_corporate_registration_valid, jp_driver_license_valid, imei_valid, mac_address_valid, ipv4_public,
  not_repeating_pattern, credit_card_bin_valid,
  english_name_valid, korean_address_valid, japanese_address_valid, chinese_address_valid
};

module.exports = { ...VERIFICATION_FUNCTIONS, VERIFICATION_FUNCTIONS, setCustomData,
  getVerificationFunction: (name) => VERIFICATION_FUNCTIONS[name],
  registerVerificationFunction: (name, func) => { VERIFICATION_FUNCTIONS[name] = func; }
};
