// 백엔드 API(/api/*) 호출을 담당하는 클라이언트.
// 백엔드는 NEIS_API_KEY를 직접 다루므로 프론트엔드는 이 API만 사용한다.

export type SchoolSummary = {
  school_code: string;
  edu_office_code: string;
  school_name: string;
  edu_office_name: string;
  location_name: string;
  school_kind_name: string;
};

export type MealInfo = {
  meal_date: string;
  menu_items: string[];
  origin_items: string[];
  nutrition_items: string[];
  calorie_info: string | null;
  meal_headcount: string | null;
};

export type MealSearchResponse = {
  school_code: string;
  edu_office_code: string;
  from_date: string;
  to_date: string;
  meals: MealInfo[];
};

export class ApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function parseErrorResponse(response: Response): Promise<never> {
  let code = "UNKNOWN";
  let message = "요청 처리 중 오류가 발생했습니다.";
  try {
    const body = await response.json();
    if (body?.detail?.code) {
      code = body.detail.code;
      message = body.detail.message ?? message;
    }
  } catch {
    // 응답 본문이 JSON이 아닌 경우 기본 메시지를 사용한다.
  }
  throw new ApiError(code, message);
}

export async function searchSchools(name: string): Promise<SchoolSummary[]> {
  const params = new URLSearchParams({ name });
  const response = await fetch(`/api/schools?${params.toString()}`);
  if (!response.ok) {
    await parseErrorResponse(response);
  }
  const body = await response.json();
  return body.schools as SchoolSummary[];
}

export async function searchMeals(
  eduOfficeCode: string,
  schoolCode: string,
  fromDate: string,
  toDate: string,
): Promise<MealSearchResponse> {
  const params = new URLSearchParams({
    edu_office_code: eduOfficeCode,
    school_code: schoolCode,
    from_date: fromDate,
    to_date: toDate,
  });
  const response = await fetch(`/api/meals?${params.toString()}`);
  if (!response.ok) {
    await parseErrorResponse(response);
  }
  return (await response.json()) as MealSearchResponse;
}

export type TimetablePeriod = { period: string | null; subject: string; teacher: string };
export type TimetableResponse = { date: string; periods: TimetablePeriod[] };

export async function searchTimetable(
  school: SchoolSummary,
  schoolKind: string,
  grade: string,
  className: string,
  date: string,
): Promise<TimetableResponse> {
  const params = new URLSearchParams({
    edu_office_code: school.edu_office_code,
    school_code: school.school_code,
    school_kind: schoolKind,
    grade,
    class_name: className,
    date_ymd: date,
  });
  const response = await fetch(`/api/timetable?${params.toString()}`);
  if (!response.ok) await parseErrorResponse(response);
  return (await response.json()) as TimetableResponse;
}
