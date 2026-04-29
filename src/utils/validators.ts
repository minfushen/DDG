// 验证统一社会信用代码
export function validateCreditCode(code: string): boolean {
  // 18位统一社会信用代码
  const pattern = /^[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}$/;
  return pattern.test(code);
}

// 验证企业名称
export function validateEnterpriseName(name: string): boolean {
  // 企业名称至少2个字符，最多50个字符
  return name.length >= 2 && name.length <= 50;
}

// 验证金额
export function validateAmount(amount: string): boolean {
  const num = parseFloat(amount);
  return !isNaN(num) && num > 0;
}

// 验证日期范围
export function validateDateRange(start: string, end: string): boolean {
  const startDate = new Date(start);
  const endDate = new Date(end);
  return startDate <= endDate;
}