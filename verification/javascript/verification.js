/**
 * Verification functions for additional validation after regex matching.
 * This module provides additional validation beyond regex matching.
 * All verification functions follow the signature: (value: string) => boolean
 */

// --- Data Cache for Heuristics and Custom Data ---
const _DATA_CACHE = new Map();

/**
 * Load values from a data source.
 * In this implementation, it returns data from _DATA_CACHE.
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

// --- Constants for CJK Name Verification ---

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
  "电话", "電話", "邮箱", "郵箱", "地址", "姓名", "信息", "資訊", "联系", "聯繫", "手机", "手機", "号码", "號碼", "传真", "傳真", "邮件", "郵件", "密码", "密碼", "账号", "帳號", "注册", "註冊", "登录", "登錄", "确认", "確認", "验证", "驗證", "性别", "性別", "生日", "职业", "職業", "公司", "部门", "部門"
]);

const KOREAN_NON_NAME_KEYWORDS = new Set([
  "전화번호", "이메일", "연락처", "주소", "이름", "성명", "휴대폰", "핸드폰", "번호", "전화", "메일", "팩스", "모바일", "정보", "문의", "확인", "성별", "생년", "월일", "생일", "직업", "나이", "회사", "부서", "직책", "전화번", "메일주", "이메일주", "연락처는", "주소는", "이름은", "성명은"
]);

const JAPANESE_NON_NAME_KEYWORDS = new Set([
  "田園", "田畑", "田舎", "中心", "中央", "中間", "中古", "中止", "中国", "中学", "山脈", "山岳", "山林", "山地", "山頂", "高速", "高校", "高層", "高価", "高原", "高齢", "林業", "林道", "森林", "石油", "石材", "石炭", "石器", "金属", "金融", "金額", "金銭", "金庫", "上記", "上昇", "上手", "上司", "大学", "大会", "大臣", "大量", "大型", "大切", "大変", "小学", "小説", "小型", "小売", "原因", "原則", "原料", "原発", "内容", "内部", "内閣", "前回", "前者", "前提", "前日", "後半", "後者", "後日", "西洋", "西側", "青年", "青春", "近代", "近年", "近所", "遠方", "遠足", "池袋",
  "電話", "住所", "名前", "情報", "連絡", "番号", "携帯", "確認", "登録", "氏名", "性別", "生年", "職業", "会社", "部署", "郵便", "暗号", "認証", "口座"]);

// --- Core Verification Functions ---

/**
 * Verify IBAN using Mod-97 check algorithm.
 */
function iban_mod97(value) {
  const iban = value.replace(/\s/g, "").toUpperCase();
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

/**
 * Verify using Luhn algorithm (mod-10 checksum).
 */
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

/**
 * Verify DMS (Degrees Minutes Seconds) coordinate format.
 */
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

/**
 * Verify token has high entropy characteristics.
 */
function high_entropy_token(value) {
  if (value.length < 20) return false;
  if (/\s/.test(value)) return false;

  const allowedChars = /^[A-Za-z0-9_\-+/./=]+$/;
  if (!allowedChars.test(value)) return false;

  const charCounts = {};
  for (const char of value) {
    charCounts[char] = (charCounts[char] || 0) + 1;
  }

  const length = value.length;
  let entropy = 0;
  for (const count of Object.values(charCounts)) {
    const p = count / length;
    entropy -= p * Math.log2(p);
  }

  return entropy >= 4.0;
}

/**
 * Verify that a numeric string is NOT a timestamp.
 */
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

/**
 * Verify Korean postal code is valid.
 */
function korean_zipcode_valid(value) {
  const digitsOnly = value.replace(/\D/g, "");
  
  const validZips = _loadData("kr_zipcodes.csv");
  if (validZips.size > 0) {
    return validZips.has(value) || validZips.has(digitsOnly);
  }

  if (digitsOnly.length !== 5) return false;

  let isSequentialUp = true;
  let isSequentialDown = true;
  for (let i = 1; i < digitsOnly.length; i++) {
    if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) + 1) isSequentialUp = false;
    if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) - 1) isSequentialDown = false;
  }
  if (isSequentialUp || isSequentialDown) return false;

  if (new Set(digitsOnly).size === 1) return false;

  return true;
}

/**
 * Verify US postal code is valid.
 */
function us_zipcode_valid(value) {
  const digitsOnly = value.replace(/\D/g, "");
  
  const validZips = _loadData("us_zipcodes.csv");
  if (validZips.size > 0) {
    if (digitsOnly.length === 5) return validZips.has(digitsOnly);
    if (digitsOnly.length === 9) return validZips.has(digitsOnly.slice(0, 5));
  }

  if (digitsOnly.length !== 5 && digitsOnly.length !== 9) return false;

  const baseZip = digitsOnly.slice(0, 5);
  let isSequentialUp = true;
  let isSequentialDown = true;
  for (let i = 1; i < baseZip.length; i++) {
    if (parseInt(baseZip[i], 10) !== parseInt(baseZip[i-1], 10) + 1) isSequentialUp = false;
    if (parseInt(baseZip[i], 10) !== parseInt(baseZip[i-1], 10) - 1) isSequentialDown = false;
  }
  if (isSequentialUp || isSequentialDown) return false;

  if (new Set(baseZip).size === 1) return false;

  return true;
}

/**
 * Verify Japanese postal code is valid.
 */
function jp_zipcode_valid(value) {
  const digitsOnly = value.replace(/[-−‐]/g, "").replace(/\D/g, "");
  if (digitsOnly.length !== 7) return false;

  const validZips = _loadData("jp_zipcodes.csv");
  if (validZips.size > 0) {
    const hyphenFormat = `${digitsOnly.slice(0, 3)}-${digitsOnly.slice(3)}`;
    return validZips.has(hyphenFormat) || validZips.has(digitsOnly);
  }

  if (new Set(digitsOnly).size === 1) return false;

  let isSequentialUp = true;
  let isSequentialDown = true;
  for (let i = 1; i < digitsOnly.length; i++) {
    if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) + 1) isSequentialUp = false;
    if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) - 1) isSequentialDown = false;
  }
  if (isSequentialUp || isSequentialDown) return false;

  return true;
}

/**
 * Verify Chinese postal code is valid.
 */
function cn_zipcode_valid(value) {
  const digitsOnly = value.replace(/\D/g, "");
  if (digitsOnly.length !== 6) return false;

  const validZips = _loadData("cn_zipcodes.csv");
  if (validZips.size > 0) return validZips.has(digitsOnly);

  if (new Set(digitsOnly).size === 1) return false;

  let isSequentialUp = true;
  let isSequentialDown = true;
  for (let i = 1; i < digitsOnly.length; i++) {
    if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) + 1) isSequentialUp = false;
    if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) - 1) isSequentialDown = false;
  }
  if (isSequentialUp || isSequentialDown) return false;

  const firstTwo = parseInt(digitsOnly.slice(0, 2), 10);
  if (firstTwo < 1 || firstTwo > 86) return false;

  return true;
}

/**
 * Verify Taiwan postal code is valid.
 */
function tw_zipcode_valid(value) {
  const digitsOnly = value.replace(/\D/g, "");
  if (digitsOnly.length !== 3 && digitsOnly.length !== 5) return false;

  const validZips = _loadData("tw_zipcodes.csv");
  if (validZips.size > 0) {
    if (validZips.has(digitsOnly)) return true;
    if (digitsOnly.length === 5 && validZips.has(digitsOnly.slice(0, 3))) return true;
    return false;
  }

  if (new Set(digitsOnly).size === 1) return false;

  const firstDigit = parseInt(digitsOnly[0], 10);
  if (firstDigit === 0) return false;

  return true;
}

/**
 * Verify Indian PIN code is valid.
 */
function in_pincode_valid(value) {
  const digitsOnly = value.replace(/\D/g, "");
  if (digitsOnly.length !== 6) return false;
  if (digitsOnly[0] === '0') return false;

  const validPins = _loadData("in_pincodes.csv");
  if (validPins.size > 0) return validPins.has(digitsOnly);

  if (new Set(digitsOnly).size === 1) return false;

  let isSequentialUp = true;
  let isSequentialDown = true;
  for (let i = 1; i < digitsOnly.length; i++) {
    if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) + 1) isSequentialUp = false;
    if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) - 1) isSequentialDown = false;
  }
  if (isSequentialUp || isSequentialDown) return false;

  return true;
}

/**
 * Verify Korean bank account is valid and not a timestamp.
 */
function korean_bank_account_valid(value) {
  const digitsOnly = value.replace(/\D/g, "");
  if (!digitsOnly) return false;

  const length = digitsOnly.length;
  const knownPrefixes = ["110", "120", "150", "190", "830", "1002", "301", "3333", "100"];
  let hasKnownPrefix = false;
  for (const prefix of knownPrefixes) {
    if (digitsOnly.startsWith(prefix)) {
      hasKnownPrefix = true;
      break;
    }
  }

  if (hasKnownPrefix) {
    if (length === 10) {
      const num = parseInt(digitsOnly, 10);
      if (num >= 1600000000 && num <= 1800000000) return false;
    }
    return true;
  }

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
    if (year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31) return false;
  }

  if (length >= 10 && !hasKnownPrefix) {
    let maxSequential = 0;
    let currentSequential = 0;
    for (let i = 1; i < digitsOnly.length; i++) {
      if (parseInt(digitsOnly[i], 10) === parseInt(digitsOnly[i-1], 10) + 1) {
        currentSequential++;
        maxSequential = Math.max(maxSequential, currentSequential);
      } else {
        currentSequential = 0;
      }
    }
    if (maxSequential >= 6) return false;
  }

  return true;
}

/**
 * Verify that a numeric string is likely NOT a timestamp.
 */
function generic_number_not_timestamp(value) {
  const hasSeparators = /[- /]/.test(value);
  const digitsOnly = value.replace(/\D/g, "");
  if (!digitsOnly) return true;

  const length = digitsOnly.length;

  if (hasSeparators) {
    if (length >= 14) {
      const year = parseInt(digitsOnly.slice(0, 4), 10);
      const month = parseInt(digitsOnly.slice(4, 6), 10);
      const day = parseInt(digitsOnly.slice(6, 8), 10);
      if (year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31) return false;
    }
    return true;
  }

  if (length === 10) {
    const num = parseInt(digitsOnly, 10);
    if (num >= 1000000000 && num <= 9999999999) return false;
  }
  if (length === 13) {
    const num = parseInt(digitsOnly, 10);
    if (num >= 1000000000000 && num <= 9999999999999) return false;
  }
  if (length >= 14) {
    const year = parseInt(digitsOnly.slice(0, 4), 10);
    const month = parseInt(digitsOnly.slice(4, 6), 10);
    const day = parseInt(digitsOnly.slice(6, 8), 10);
    if (year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31) return false;
  }

  return true;
}

/**
 * Verify that the value contains at least one letter.
 */
function contains_letter(value) {
  return /\p{L}/u.test(value);
}

/**
 * Verify US SSN is valid.
 */
function us_ssn_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 9) return false;

  const area = parseInt(digits.slice(0, 3), 10);
  const group = parseInt(digits.slice(3, 5), 10);
  const serial = parseInt(digits.slice(5, 9), 10);

  if (area === 0 || area === 666 || area >= 900) return false;
  if (group === 0) return false;
  if (serial === 0) return false;

  return true;
}

/**
 * Verify Chinese name has a valid surname prefix and given name.
 */
function chinese_name_valid(value) {
  if (!value || value.length < 2 || value.length > 4) return false;
  if (CHINESE_NON_NAME_KEYWORDS.has(value)) return false;

  let surname = null;
  let givenName = null;

  if (value.length >= 3 && CHINESE_SURNAMES.has(value.slice(0, 2))) {
    surname = value.slice(0, 2);
    givenName = value.slice(2);
  } else if (CHINESE_SURNAMES.has(value[0])) {
    surname = value[0];
    givenName = value.slice(1);
  }

  if (!surname) return false;

  const validGivenNames = _loadData("cn_given_names.csv");
  if (validGivenNames.size > 0 && validGivenNames.has(givenName)) return true;

  if (value.length < 2 || value.length > 4) return false;

  return true;
}

/**
 * Verify Korean name has a valid surname prefix.
 */
function korean_name_valid(value) {
  if (!value || value.length < 2 || value.length > 5) return false;
  if (KOREAN_NON_NAME_KEYWORDS.has(value)) return false;

  const particles = ["은", "는", "이", "가", "을", "를", "의"];
  if (value.length >= 3 && particles.includes(value[value.length - 1])) {
    if (KOREAN_NON_NAME_KEYWORDS.has(value.slice(0, -1))) return false;
  }

  let surname = null;
  let givenName = null;

  if (value.length >= 3 && KOREAN_SURNAMES.has(value.slice(0, 2))) {
    surname = value.slice(0, 2);
    givenName = value.slice(2);
  } else if (KOREAN_SURNAMES.has(value[0])) {
    surname = value[0];
    givenName = value.slice(1);
  }

  if (!surname) return false;

  const validGivenNames = _loadData("kr_given_names.csv");
  if (validGivenNames.size > 0 && validGivenNames.has(givenName)) return true;

  if (value.length !== 3) return false;

  return true;
}

/**
 * Verify Japanese name (kanji) matches known surname patterns.
 */
function japanese_name_kanji_valid(value) {
  if (!value || value.length < 2 || value.length > 6) return false;
  if (JAPANESE_NON_NAME_KEYWORDS.has(value)) return false;

  if (value.length === 2) return JAPANESE_SURNAMES.has(value);

  let surname = null;
  let givenName = null;

  if (value.length >= 4 && JAPANESE_SURNAMES.has(value.slice(0, 3))) {
    surname = value.slice(0, 3);
    givenName = value.slice(3);
  } else if (value.length >= 2 && JAPANESE_SURNAMES.has(value.slice(0, 2))) {
    surname = value.slice(0, 2);
    givenName = value.slice(2);
  } else if (JAPANESE_SURNAMES.has(value[0])) {
    surname = value[0];
    givenName = value.slice(1);
  }

  if (!surname) return false;

  const validGivenNames = _loadData("jp_given_names.csv");
  if (validGivenNames.size > 0 && validGivenNames.has(givenName)) return true;

  if (value.length !== 3 && value.length !== 4) return false;

  return true;
}

/**
 * Verify that a CJK name match is standalone.
 */
function cjk_name_standalone(value) {
  if (!value || value.length > 6) return false;

  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    const isCjk = (
      (code >= 0x4E00 && code <= 0x9FFF) || // CJK Unified Ideographs
      (code >= 0xAC00 && code <= 0xD7AF) || // Korean Hangul
      (code >= 0x3040 && code <= 0x309F) || // Hiragana
      (code >= 0x30A0 && code <= 0x30FF)    // Katakana
    );
    if (!isCjk) return false;
  }
  return true;
}

/**
 * Verify Chinese National ID using checksum.
 */
function cn_national_id_valid(value) {
  const idStr = value.replace(/\s/g, "").toUpperCase();
  if (idStr.length !== 18) return false;

  const validProvinces = new Set([
    "11", "12", "13", "14", "15", "21", "22", "23", "31", "32", "33", "34", "35", "36", "37",
    "41", "42", "43", "44", "45", "46", "50", "51", "52", "53", "54", "61", "62", "63", "64", "65",
    "71", "81", "82", "91"
  ]);

  if (!validProvinces.has(idStr.slice(0, 2))) return false;

  const year = parseInt(idStr.slice(6, 10), 10);
  const month = parseInt(idStr.slice(10, 12), 10);
  const day = parseInt(idStr.slice(12, 14), 10);

  if (!_isValidDate(year, month, day)) return false;

  const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
  const checkDigits = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"];

  let total = 0;
  for (let i = 0; i < 17; i++) {
    total += parseInt(idStr[i], 10) * weights[i];
  }
  const expectedCheck = checkDigits[total % 11];
  return idStr[17] === expectedCheck;
}

/**
 * Verify Taiwan National ID using checksum.
 */
function tw_national_id_valid(value) {
  const idStr = value.replace(/\s/g, "").toUpperCase();
  if (idStr.length !== 10) return false;
  if (!/^[A-Z]$/.test(idStr[0])) return false;
  if (!/^\d{9}$/.test(idStr.slice(1))) return false;

  if (["I", "O", "W"].includes(idStr[0])) return false;

  const letterCode = idStr.charCodeAt(0) - "A".charCodeAt(0) + 10;
  const gender = parseInt(idStr[1], 10);
  if (gender !== 1 && gender !== 2) return false;

  const firstDigit = Math.floor(letterCode / 10);
  const secondDigit = letterCode % 10;
  let total = firstDigit * 1 + secondDigit * 9;

  const weights = [8, 7, 6, 5, 4, 3, 2, 1];
  for (let i = 0; i < weights.length; i++) {
    total += parseInt(idStr[i + 1], 10) * weights[i];
  }
  total += parseInt(idStr[9], 10);

  return total % 10 === 0;
}

/**
 * Verify India Aadhaar number using Verhoeff checksum.
 */
function india_aadhaar_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 12) return false;
  if (digits[0] === '0' || digits[0] === '1') return false;
  if (new Set(digits).size === 1) return false;

  const d = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
  ];
  const p = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
  ];

  let c = 0;
  const reversedDigits = digits.split("").reverse();
  for (let i = 0; i < reversedDigits.length; i++) {
    c = d[c][p[i % 8][parseInt(reversedDigits[i], 10)]];
  }
  return c === 0;
}

/**
 * Verify India PAN format.
 */
function india_pan_valid(value) {
  const pan = value.replace(/\s/g, "").toUpperCase();
  if (pan.length !== 10) return false;
  if (!/^[A-Z]{5}\d{4}[A-Z]$/.test(pan)) return false;

  const validEntityTypes = new Set(["A", "B", "C", "F", "G", "H", "J", "K", "L", "P", "T"]);
  if (!validEntityTypes.has(pan[3])) return false;

  if (["AAAAA", "ABCDE", "XXXXX", "ZZZZZ"].includes(pan.slice(0, 5))) return false;

  return true;
}

/**
 * Verify Korean Business Registration Number checksum.
 */
function kr_business_registration_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 10) return false;
  if (new Set(digits).size === 1) return false;

  const weights = [1, 3, 7, 1, 3, 7, 1, 3, 5];
  let total = 0;
  for (let i = 0; i < 9; i++) {
    const digit = parseInt(digits[i], 10);
    total += digit * weights[i];
    if (i === 8) total += Math.floor((digit * 5) / 10);
  }
  const checkDigit = (10 - (total % 10)) % 10;
  return parseInt(digits[9], 10) === checkDigit;
}

/**
 * Verify Korean Resident Registration Number (RRN).
 */
function kr_rrn_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 13) return false;

  const yy = parseInt(digits.slice(0, 2), 10);
  const mm = parseInt(digits.slice(2, 4), 10);
  const dd = parseInt(digits.slice(4, 6), 10);
  const genderCentury = parseInt(digits[6], 10);

  if (genderCentury < 1 || genderCentury > 4) return false;

  const year = (genderCentury === 1 || genderCentury === 2) ? 1900 + yy : 2000 + yy;
  if (!_isValidDate(year, mm, dd)) return false;
  if (new Set(digits).size === 1) return false;

  const weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5];
  let total = 0;
  for (let i = 0; i < 12; i++) {
    total += parseInt(digits[i], 10) * weights[i];
  }
  const checkDigit = (11 - (total % 11)) % 10;
  return parseInt(digits[12], 10) === checkDigit;
}

/**
 * Verify Korean Alien Registration Number.
 */
function kr_alien_registration_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 13) return false;

  const yy = parseInt(digits.slice(0, 2), 10);
  const mm = parseInt(digits.slice(2, 4), 10);
  const dd = parseInt(digits.slice(4, 6), 10);
  const genderCentury = parseInt(digits[6], 10);

  if (genderCentury < 5 || genderCentury > 8) return false;

  const year = (genderCentury === 5 || genderCentury === 6) ? 1900 + yy : 2000 + yy;
  if (!_isValidDate(year, mm, dd)) return false;
  if (new Set(digits).size === 1) return false;

  return true;
}

/**
 * Verify Japanese My Number checksum.
 */
function jp_my_number_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 12) return false;
  if (new Set(digits).size === 1) return false;
  if (digits === "123456789012" || digits === "012345678901") return false;

  const weights = [6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  let total = 0;
  for (let i = 0; i < 11; i++) {
    total += parseInt(digits[i], 10) * weights[i];
  }
  const remainder = total % 11;
  const expectedCheck = remainder <= 1 ? 0 : 11 - remainder;
  return parseInt(digits[11], 10) === expectedCheck;
}

/**
 * Verify Korean Corporate Registration Number checksum.
 */
function kr_corporate_registration_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 13) return false;
  if (new Set(digits).size === 1) return false;

  const weights = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2];
  let total = 0;
  for (let i = 0; i < 12; i++) {
    let product = parseInt(digits[i], 10) * weights[i];
    if (product > 9) product -= 9;
    total += product;
  }
  const checkDigit = (10 - (total % 10)) % 10;
  return parseInt(digits[12], 10) === checkDigit;
}

/**
 * Verify Spanish DNI checksum.
 */
function spain_dni_valid(value) {
  const dni = value.replace(/\s/g, "").toUpperCase();
  if (dni.length !== 9) return false;
  if (!/^\d{8}[A-Z]$/.test(dni)) return false;

  const letters = "TRWAGMYFPDXBNJZSQVHLCKE";
  const number = parseInt(dni.slice(0, 8), 10);
  return dni[8] === letters[number % 23];
}

/**
 * Verify Spanish NIE checksum.
 */
function spain_nie_valid(value) {
  const nie = value.replace(/\s/g, "").toUpperCase();
  if (nie.length !== 9) return false;
  if (!/^[XYZ]\d{7}[A-Z]$/.test(nie)) return false;

  const replacements = { "X": "0", "Y": "1", "Z": "2" };
  const numberStr = replacements[nie[0]] + nie.slice(1, 8);
  const letters = "TRWAGMYFPDXBNJZSQVHLCKE";
  const number = parseInt(numberStr, 10);
  return nie[8] === letters[number % 23];
}

/**
 * Verify Dutch BSN using 11-proof algorithm.
 */
function netherlands_bsn_valid(value) {
  let digits = value.replace(/\D/g, "");
  if (digits.length === 8) digits = "0" + digits;
  else if (digits.length !== 9) return false;

  if (new Set(digits).size === 1) return false;

  const weights = [9, 8, 7, 6, 5, 4, 3, 2, -1];
  let total = 0;
  for (let i = 0; i < 9; i++) {
    total += parseInt(digits[i], 10) * weights[i];
  }
  return total % 11 === 0;
}

/**
 * Verify Polish PESEL checksum.
 */
function poland_pesel_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 11) return false;
  if (new Set(digits).size === 1) return false;

  const yy = parseInt(digits.slice(0, 2), 10);
  const mm = parseInt(digits.slice(2, 4), 10);
  const dd = parseInt(digits.slice(4, 6), 10);

  let year, month;
  if (mm >= 1 && mm <= 12) { year = 1900 + yy; month = mm; }
  else if (mm >= 21 && mm <= 32) { year = 2000 + yy; month = mm - 20; }
  else if (mm >= 41 && mm <= 52) { year = 2100 + yy; month = mm - 40; }
  else if (mm >= 61 && mm <= 72) { year = 2200 + yy; month = mm - 60; }
  else if (mm >= 81 && mm <= 92) { year = 1800 + yy; month = mm - 80; }
  else return false;

  if (!_isValidDate(year, month, dd)) return false;

  const weights = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3];
  let total = 0;
  for (let i = 0; i < 10; i++) {
    total += parseInt(digits[i], 10) * weights[i];
  }
  const checkDigit = (10 - (total % 10)) % 10;
  return parseInt(digits[10], 10) === checkDigit;
}

/**
 * Verify Swedish Personnummer using Luhn algorithm.
 */
function sweden_personnummer_valid(value) {
  let digits = value.replace(/\D/g, "");
  if (digits.length === 12) digits = digits.slice(2);
  else if (digits.length !== 10) return false;

  const mm = parseInt(digits.slice(2, 4), 10);
  const dd = parseInt(digits.slice(4, 6), 10);
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return false;

  return luhn(digits);
}

/**
 * Verify French INSEE number.
 */
function france_insee_valid(value) {
  const cleaned = value.replace(/\s/g, "");
  if (cleaned.length !== 15) return false;

  let calcStr = cleaned;
  const dept = cleaned.slice(5, 7).toUpperCase();
  if (dept === "2A") calcStr = cleaned.slice(0, 5) + "19" + cleaned.slice(7);
  else if (dept === "2B") calcStr = cleaned.slice(0, 5) + "18" + cleaned.slice(7);

  if (!/^\d+$/.test(calcStr)) return false;
  if (![1, 2].includes(parseInt(calcStr[0], 10))) return false;
  const month = parseInt(calcStr.slice(3, 5), 10);
  if (month < 1 || month > 12) return false;

  const baseNumber = BigInt(calcStr.slice(0, 13));
  const expectedCheck = 97n - (baseNumber % 97n);
  const actualCheck = BigInt(calcStr.slice(13, 15));
  return actualCheck === expectedCheck;
}

/**
 * Verify Belgian RRN.
 */
function belgium_rrn_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 11) return false;

  const mm = parseInt(digits.slice(2, 4), 10);
  const dd = parseInt(digits.slice(4, 6), 10);
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return false;

  const base9 = BigInt(digits.slice(0, 9));
  const checkDigits = BigInt(digits.slice(9, 11));

  if (checkDigits === 97n - (base9 % 97n)) return true;
  const base9_2000 = BigInt("2" + digits.slice(0, 9));
  return checkDigits === 97n - (base9_2000 % 97n);
}

/**
 * Verify Finnish HETU.
 */
function finland_hetu_valid(value) {
  const hetu = value.replace(/\s/g, "").toUpperCase();
  if (hetu.length !== 11) return false;

  const dd = parseInt(hetu.slice(0, 2), 10);
  const mm = parseInt(hetu.slice(2, 4), 10);
  const yy = parseInt(hetu.slice(4, 6), 10);
  const centurySign = hetu[6];
  const individual = hetu.slice(7, 10);
  const checkChar = hetu[10];

  if (!["+", "-", "A"].includes(centurySign)) return false;
  if (!/^\d{3}$/.test(individual)) return false;

  let year;
  if (centurySign === "+") year = 1800 + yy;
  else if (centurySign === "-") year = 1900 + yy;
  else year = 2000 + yy;

  if (!_isValidDate(year, mm, dd)) return false;

  const checkSequence = "0123456789ABCDEFHJKLMNPRSTUVWXY";
  const number = parseInt(hetu.slice(0, 6) + individual, 10);
  return checkChar === checkSequence[number % 31];
  }

  /**
  * Verify Japanese Corporate Number checksum.
  * 13 digits, the 1st digit is the check digit.
  * Weights 1-2-1-2... for positions 1-12 of the base number.
  */
  function jp_corporate_number_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 13) return false;

  const checkDigit = parseInt(digits[0], 10);
  const baseDigits = digits.slice(1).split("").map(Number);

  let total = 0;
  for (let i = 0; i < 12; i++) {
    const weight = (12 - i) % 2 === 0 ? 2 : 1;
    total += baseDigits[i] * weight;
  }

  const remainder = total % 9;
  const expectedCheck = 9 - remainder;
  return checkDigit === expectedCheck;
  }

  /**
  * Verify Taiwan Unified Business Number (UBN).
  */
  function tw_ubn_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 8) return false;

  const weights = [1, 2, 1, 2, 1, 2, 4, 1];
  let total = 0;
  for (let i = 0; i < 8; i++) {
    const prod = parseInt(digits[i], 10) * weights[i];
    total += Math.floor(prod / 10) + (prod % 10);
  }

  if (total % 10 === 0) return true;
  if (digits[6] === "7" && (total + 1) % 10 === 0) return true;

  return false;
  }

  /**
  * Verify US National Provider Identifier (NPI).
  */
  function us_npi_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 10) return false;

  const fullStr = "80840" + digits.slice(0, 9);
  let luhnTotal = 0;
  const revDigits = fullStr.split("").reverse().map(Number);

  for (let i = 0; i < revDigits.length; i++) {
    let d = revDigits[i];
    if (i % 2 === 0) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    luhnTotal += d;
  }

  const expectedCheck = (10 - (luhnTotal % 10)) % 10;
  return parseInt(digits[9], 10) === expectedCheck;
  }

  /**
  * Verify UK National Insurance Number (NINO).
  */
  function uk_nino_valid(value) {
  const val = value.replace(/\s/g, "").toUpperCase();
  const pattern = /^[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\d{6}[A-D]$/;
  if (!pattern.test(val)) return false;

  const prefix = val.slice(0, 2);
  const excluded = ["BG", "GB", "KN", "NK", "NT", "TN", "ZZ"];
  if (excluded.includes(prefix)) return false;

  return true;
  }

  /**
  * Verify SWIFT/BIC code.
  */
  function swift_bic_valid(value) {
  const val = value.replace(/\s/g, "").toUpperCase();
  if (val.length !== 8 && val.length !== 11) return false;
  return /^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$/.test(val);
  }

  /**
  * Verify AWS Access Key.
  */
  function aws_access_key_valid(value) {
  if (value.length !== 20) return false;
  if (!value.startsWith("AKIA") && !value.startsWith("ASIA")) return false;
  return /^[A-Z0-9]+$/.test(value);
  }

  /**
  * Verify Google API Key.
  */
  function google_api_key_valid(value) {
  if (value.length !== 39) return false;
  if (!value.startsWith("AIza")) return false;
  return /^[A-Za-z0-9_-]{39}$/.test(value);
  }

  /**
  * Verify Bitcoin address.
  */
  function crypto_btc_valid(value) {
  if (value.length < 26 || value.length > 35) return false;
  const base58Pattern = /^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$/;
  return base58Pattern.test(value);
  }

  /**
  * Verify Ethereum address.
  */
  function crypto_eth_valid(value) {
  if (value.length !== 42) return false;
  if (!value.startsWith("0x")) return false;
  return /^0x[0-9a-fA-F]{40}$/.test(value);
  }

  /**
  * Verify IPv4 address is a public address.
  */

function ipv4_public(value) {
  const parts = value.split(".");
  if (parts.length !== 4) return false;
  const octets = parts.map(p => parseInt(p, 10));
  if (octets.some(o => isNaN(o) || o < 0 || o > 255)) return false;

  const [f, s, t, fo] = octets;
  if (f === 0 || f === 10 || f === 127) return false;
  if (f === 169 && s === 254) return false;
  if (f === 172 && s >= 16 && s <= 31) return false;
  if (f === 192 && s === 0 && t === 2) return false;
  if (f === 192 && s === 168) return false;
  if (f === 198 && s === 51 && t === 100) return false;
  if (f === 203 && s === 0 && t === 113) return false;
  if (f >= 224 && f <= 239) return false;
  if (f >= 240) return false;

  return true;
}

/**
 * Verify that a value is not a simple repeating pattern.
 */
function not_repeating_pattern(value) {
  if (!value || value.length < 4) return true;
  if (new Set(value).size === 1) return false;

  const digitsOnly = value.replace(/\D/g, "");
  if (digitsOnly.length >= 4) {
    let isAscending = true;
    let isDescending = true;
    for (let i = 1; i < digitsOnly.length; i++) {
      if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) + 1) isAscending = false;
      if (parseInt(digitsOnly[i], 10) !== parseInt(digitsOnly[i-1], 10) - 1) isDescending = false;
    }
    if (isAscending || isDescending) return false;
  }

  if (value.length >= 4) {
    const p2 = value.slice(0, 2);
    if (value.startsWith(p2.repeat(Math.floor(value.length / 2)))) {
      if (value.length % 2 === 0 || value.endsWith(p2[0])) return false;
    }
  }
  if (value.length >= 6) {
    const p3 = value.slice(0, 3);
    if (value.startsWith(p3.repeat(Math.floor(value.length / 3)))) {
      if (value.length % 3 === 0 || p3.startsWith(value.slice(-(value.length % 3)))) return false;
    }
  }
  return true;
}

/**
 * Verify credit card number has valid BIN and Luhn.
 */
function credit_card_bin_valid(value) {
  const digits = value.replace(/\D/g, "");
  if (digits.length < 13 || digits.length > 19) return false;

  let validBin = false;
  if (digits[0] === "4") validBin = true;
  else if (digits.length >= 2) {
    const p2 = parseInt(digits.slice(0, 2), 10);
    if (p2 >= 51 && p2 <= 55) validBin = true;
    else if (digits.length >= 4) {
      const p4 = parseInt(digits.slice(0, 4), 10);
      if (p4 >= 2221 && p4 <= 2720) validBin = true;
    }
  }
  if (!validBin && digits.length >= 2) {
    const p2 = parseInt(digits.slice(0, 2), 10);
    if (p2 === 34 || p2 === 37) validBin = true;
  }
  if (!validBin) {
    if (digits.startsWith("6011") || digits.startsWith("65")) validBin = true;
    else if (digits.length >= 3) {
      const p3 = parseInt(digits.slice(0, 3), 10);
      if (p3 >= 644 && p3 <= 649) validBin = true;
    }
    if (!validBin && digits.length >= 6) {
      const p6 = parseInt(digits.slice(0, 6), 10);
      if (p6 >= 622126 && p6 <= 622925) validBin = true;
    }
  }
  if (!validBin && digits.length >= 4) {
    const p4 = parseInt(digits.slice(0, 4), 10);
    if (p4 >= 3528 && p4 <= 3589) validBin = true;
  }
  if (!validBin && digits.startsWith("62")) validBin = true;
  if (!validBin && digits.length >= 2) {
    const p2 = parseInt(digits.slice(0, 2), 10);
    if (p2 === 36 || p2 === 38) validBin = true;
    else if (digits.length >= 3) {
      const p3 = parseInt(digits.slice(0, 3), 10);
      if (p3 >= 300 && p3 <= 305) validBin = true;
    }
  }

  return validBin && luhn(digits);
}

// --- Helper Functions ---

/**
 * Helper function to validate a date.
 */
function _isValidDate(year, month, day) {
  if (month < 1 || month > 12) return false;
  if (day < 1 || day > 31) return false;
  const daysInMonth = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if ((year % 4 === 0 && year % 100 !== 0) || (year % 400 === 0)) daysInMonth[2] = 29;
  return day <= daysInMonth[month];
}

// --- Registry and Exports ---

const VERIFICATION_FUNCTIONS = {
  iban_mod97,
  luhn,
  dms_coordinate,
  high_entropy_token,
  not_timestamp,
  korean_zipcode_valid,
  us_zipcode_valid,
  jp_zipcode_valid,
  cn_zipcode_valid,
  tw_zipcode_valid,
  in_pincode_valid,
  korean_bank_account_valid,
  generic_number_not_timestamp,
  contains_letter,
  us_ssn_valid,
  chinese_name_valid,
  korean_name_valid,
  japanese_name_kanji_valid,
  cjk_name_standalone,
  cn_national_id_valid,
  tw_national_id_valid,
  india_aadhaar_valid,
  india_pan_valid,
  kr_business_registration_valid,
  kr_rrn_valid,
  kr_alien_registration_valid,
  jp_my_number_valid,
  kr_corporate_registration_valid,
  jp_corporate_number_valid,
  tw_ubn_valid,
  us_npi_valid,
  uk_nino_valid,
  swift_bic_valid,
  aws_access_key_valid,
  google_api_key_valid,
  crypto_btc_valid,
  crypto_eth_valid,
  spain_dni_valid,
  spain_nie_valid,
  netherlands_bsn_valid,
  poland_pesel_valid,
  sweden_personnummer_valid,
  france_insee_valid,
  belgium_rrn_valid,
  finland_hetu_valid,
  ipv4_public,
  not_repeating_pattern,
  credit_card_bin_valid
};

module.exports = {
  ...VERIFICATION_FUNCTIONS,
  VERIFICATION_FUNCTIONS,
  setCustomData,
  getVerificationFunction: (name) => VERIFICATION_FUNCTIONS[name],
  registerVerificationFunction: (name, func) => {
    VERIFICATION_FUNCTIONS[name] = func;
  }
};
