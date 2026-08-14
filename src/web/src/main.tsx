import {
  Button,
  Card,
  Field,
  Input,
  Link,
  MessageBar,
  SearchBox,
  Spinner,
  Switch,
  Subtitle1,
  Tab,
  TabList,
  Text,
  Title1,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowRightRegular,
  CalendarMonthRegular,
  CalendarLtrRegular,
  FoodRegular,
  MegaphoneLoudRegular,
  SearchRegular,
  SparkleRegular,
} from "@fluentui/react-icons";
import { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { ApiError, searchMeals, searchSchools, searchTimetable, type MealInfo, type SchoolSummary, type TimetableResponse } from "./api";
import "./styles.css";

const MAX_RANGE_DAYS = 31;
const SEARCH_DEBOUNCE_MS = 300;

const schoolEvents = [
  { date: "5월 20일 (화)", title: "1학기 중간고사", detail: "1·2학년 국어, 수학" },
  { date: "5월 23일 (금)", title: "재량휴업일", detail: "학교 일정에 따라 급식이 제공되지 않습니다." },
];

const useStyles = makeStyles({
  searchIcon: { color: tokens.colorBrandForeground1 },
  tab: { minWidth: "132px" },
});

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function addDaysIso(iso: string, days: number): string {
  const date = new Date(iso);
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function formatMealDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString("ko-KR", { month: "long", day: "numeric", weekday: "short" });
}

function App() {
  const styles = useStyles();
  const [query, setQuery] = useState("");
  const [schools, setSchools] = useState<SchoolSummary[]>([]);
  const [schoolsLoading, setSchoolsLoading] = useState(false);
  const [schoolsError, setSchoolsError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SchoolSummary | null>(null);

  const [startDate, setStartDate] = useState(todayIso());
  const [endDate, setEndDate] = useState(addDaysIso(todayIso(), 4));
  const [dateError, setDateError] = useState<string | null>(null);

  const [meals, setMeals] = useState<MealInfo[] | null>(null);
  const [mealsLoading, setMealsLoading] = useState(false);
  const [mealsError, setMealsError] = useState<string | null>(null);
  const [grade, setGrade] = useState("1");
  const [className, setClassName] = useState("1");
  const [timetableDate, setTimetableDate] = useState(todayIso());
  const [timetable, setTimetable] = useState<TimetableResponse | null>(null);
  const [timetableLoading, setTimetableLoading] = useState(false);
  const [timetableError, setTimetableError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState("lookup");
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [allergyFilter, setAllergyFilter] = useState("");

  // 학교 이름 검색: 300ms debounce 후 백엔드 /api/schools 호출.
  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setSchools([]);
      setSchoolsError(null);
      return;
    }

    setSchoolsLoading(true);
    setSchoolsError(null);
    const timer = window.setTimeout(async () => {
      try {
        const result = await searchSchools(trimmed);
        setSchools(result);
      } catch (error) {
        setSchools([]);
        setSchoolsError(error instanceof ApiError ? error.message : "학교 검색 중 오류가 발생했습니다.");
      } finally {
        setSchoolsLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [query]);

  const rangeDays = useMemo(() => {
    const from = new Date(startDate);
    const to = new Date(endDate);
    return Math.round((to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24)) + 1;
  }, [startDate, endDate]);

  useEffect(() => {
    if (endDate < startDate) {
      setDateError("종료일은 시작일보다 빠를 수 없습니다.");
    } else if (rangeDays > MAX_RANGE_DAYS) {
      setDateError(`조회 기간은 최대 ${MAX_RANGE_DAYS}일까지 가능합니다.`);
    } else {
      setDateError(null);
    }
  }, [startDate, endDate, rangeDays]);

  const handleSearchMeals = async () => {
    if (!selected || dateError) return;
    setMealsLoading(true);
    setMealsError(null);
    setMeals(null);
    try {
      const result = await searchMeals(selected.edu_office_code, selected.school_code, startDate, endDate);
      setMeals(result.meals);
    } catch (error) {
      setMealsError(error instanceof ApiError ? error.message : "급식 정보를 불러오지 못했습니다.");
    } finally {
      setMealsLoading(false);
    }
  };

  const handleSearchTimetable = async () => {
    if (!selected) return;
    setTimetableLoading(true);
    setTimetableError(null);
    try {
      setTimetable(await searchTimetable(selected, selected.school_kind_name, grade, className, timetableDate));
    } catch (error) {
      setTimetableError(error instanceof ApiError ? error.message : "시간표를 불러오지 못했습니다.");
    } finally {
      setTimetableLoading(false);
    }
  };
  const filteredMeals = useMemo(
    () =>
      (meals ?? []).filter(
        (meal) => !allergyFilter || meal.nutrition_items.some((item) => item.includes(allergyFilter)),
      ),
    [meals, allergyFilter],
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><FoodRegular /></div>
          <div>
            <Text weight="bold" size={400}>급식배틀</Text>
            <Text className="brand-caption" size={200}>오늘의 학교 점심을 한눈에</Text>
          </div>
        </div>
        <TabList selectedValue={activeTab} onTabSelect={(_, data) => setActiveTab(String(data.value))}>
          <Tab className={styles.tab} value="lookup">학교 급식 조회</Tab>
          <Tab className={styles.tab} value="analysis" icon={<SparkleRegular />}>급식 분석</Tab>
        </TabList>
        <Link className="help-link">도움말</Link>
      </header>

      <main className="content">
        <section className="hero">
          <div className="hero-copy">
            <Text className="eyebrow">NEIS 공공데이터 기반</Text>
            <Title1>오늘 점심, 어디서<br /><span>무엇을 먹을까요?</span></Title1>
            <Text className="hero-description">학교를 검색하고 원하는 기간의 중식 메뉴를<br />빠르고 편하게 확인해 보세요.</Text>
          </div>
          <div className="hero-art" aria-hidden="true"><div className="sun" /><div className="plate">🍱</div></div>
        </section>

        {activeTab === "lookup" ? (
          <>
            <section className="panel search-panel">
              <div className="section-heading">
                <div className="step-badge">1</div>
                <div><Subtitle1>학교를 찾아보세요</Subtitle1><Text size={200}>학교 이름의 일부만 입력해도 검색할 수 있어요.</Text></div>
              </div>
              <SearchBox
                className="school-search"
                size="large"
                placeholder="학교 이름을 입력하세요"
                value={query}
                onChange={(_, data) => setQuery(data.value)}
                contentBefore={<SearchRegular className={styles.searchIcon} />}
              />
              {schoolsLoading && <div className="state-row"><Spinner size="tiny" /><Text size={200}>검색 중...</Text></div>}
              {schoolsError && <MessageBar intent="error">{schoolsError}</MessageBar>}
              {!schoolsLoading && !schoolsError && query.trim() && schools.length === 0 && (
                <Text size={200} className="empty-state">검색 결과가 없어요. 학교 이름을 다시 확인해 주세요.</Text>
              )}
              <div className="school-list">
                {schools.map((school) => (
                  <Card
                    key={school.school_code}
                    className={`school-card ${selected?.school_code === school.school_code ? "selected" : ""}`}
                    onClick={() => setSelected(school)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setSelected(school); }}
                  >
                    <div className="school-card-main">
                      <div className="school-icon">{school.school_kind_name.includes("고") ? "고" : school.school_kind_name.includes("중") ? "중" : "초"}</div>
                      <div><Text weight="semibold">{school.school_name}</Text><Text size={200}>{school.edu_office_name} · {school.location_name}</Text></div>
                    </div>
                    {selected?.school_code === school.school_code && <div className="selected-dot" />}
                  </Card>
                ))}
              </div>
            </section>

            <section className="panel date-panel">
              <div className="section-heading">
                <div className="step-badge">2</div>
                <div><Subtitle1>조회 기간을 선택하세요</Subtitle1><Text size={200}>최대 31일까지 선택할 수 있어요.</Text></div>
              </div>
              {selected ? (
                <div className="selected-school">
                  <div className="mini-school-icon">{selected.school_kind_name.includes("고") ? "고" : selected.school_kind_name.includes("중") ? "중" : "초"}</div>
                  <div><Text size={200}>선택한 학교</Text><Text weight="semibold">{selected.school_name}</Text></div>
                  <Button appearance="subtle" onClick={() => setSelected(null)}>변경</Button>
                </div>
              ) : (
                <Text size={200} className="empty-state">먼저 학교를 선택해 주세요.</Text>
              )}
              <div className="date-fields">
                <Field label="시작일" validationState={dateError ? "error" : "none"}>
                  <Input type="date" value={startDate} onChange={(_, data) => setStartDate(data.value)} contentBefore={<CalendarLtrRegular />} />
                </Field>
                <span className="date-separator">—</span>
                <Field label="종료일" validationState={dateError ? "error" : "none"}>
                  <Input type="date" value={endDate} onChange={(_, data) => setEndDate(data.value)} contentBefore={<CalendarLtrRegular />} />
                </Field>
                <Button
                  appearance="primary"
                  size="large"
                  icon={<ArrowRightRegular />}
                  disabled={!selected || !!dateError || mealsLoading}
                  onClick={handleSearchMeals}
                >
                  급식 정보 조회
                </Button>
              </div>
              {dateError && <MessageBar intent="warning" className="notice">{dateError}</MessageBar>}
            </section>

            <section className="results">
              <div className="results-heading">
                <div>
                  <Text className="eyebrow">선택한 기간의 중식</Text>
                  <Subtitle1>{selected ? `${selected.school_name} · ${startDate} — ${endDate}` : "학교를 먼저 선택해 주세요"}</Subtitle1>
                </div>
              </div>
              {mealsLoading && <div className="state-row"><Spinner size="tiny" /><Text size={200}>급식 정보를 불러오는 중...</Text></div>}
              {mealsError && <MessageBar intent="error">{mealsError}</MessageBar>}
              {!mealsLoading && !mealsError && meals !== null && meals.length === 0 && (
                <Text size={200} className="empty-state">선택한 기간에 급식 정보가 없어요.</Text>
              )}
              <div className="meal-grid">
                {filteredMeals.map((meal) => (
                  <Card className="meal-card" key={meal.meal_date}>
                    <div className="meal-date">
                      <Text weight="semibold">{formatMealDate(meal.meal_date)}</Text>
                      <Text size={200}>{meal.calorie_info ?? ""}</Text>
                    </div>
                    <ul>{meal.menu_items.map((item) => <li key={item}>{item}</li>)}</ul>
                    {meal.origin_items.length > 0 && (
                      <Text className="meal-meta" size={200}>원산지 · {meal.origin_items.join(", ")}</Text>
                    )}
                    {meal.nutrition_items.length > 0 && (
                      <div className="allergy-row"><Text size={200}>영양정보</Text><Text size={200} weight="semibold">{meal.nutrition_items.join(" · ")}</Text></div>
                    )}
                  </Card>
                ))}
              </div>
            </section>

            <section className="panel timetable-panel">
              <div className="panel-title"><div><Text className="eyebrow">학교 시간표</Text><Subtitle1>학년·반과 날짜를 선택하세요</Subtitle1></div><CalendarMonthRegular className="panel-icon" /></div>
              <div className="timetable-fields">
                <Field label="학년"><Input type="number" min="1" max="6" value={grade} onChange={(_, data) => setGrade(data.value)} /></Field>
                <Field label="반"><Input type="number" min="1" value={className} onChange={(_, data) => setClassName(data.value)} /></Field>
                <Field label="조회일"><Input type="date" value={timetableDate} onChange={(_, data) => setTimetableDate(data.value)} /></Field>
                <Button appearance="primary" disabled={!selected || timetableLoading} onClick={handleSearchTimetable}>{timetableLoading ? "조회 중..." : "시간표 조회"}</Button>
              </div>
              {timetableError && <MessageBar intent="error">{timetableError}</MessageBar>}
              {timetable && timetable.periods.length === 0 && <Text className="empty-state" size={200}>선택한 날짜의 시간표가 없어요.</Text>}
              {timetable && timetable.periods.length > 0 && <div className="timetable-grid">{timetable.periods.map((item, index) => <Card className="period-card" key={`${item.period}-${index}`}><Text className="period-number" weight="bold">{item.period ?? index + 1}교시</Text><Text weight="semibold">{item.subject || "과목 미정"}</Text>{item.teacher && <Text size={200}>{item.teacher}</Text>}</Card>)}</div>}
            </section>            <section className="dashboard-grid">
              <div className="panel schedule-panel">
                <div className="panel-title"><div><Text className="eyebrow">학교 일정</Text><Subtitle1>이번 주 학사일정</Subtitle1></div><CalendarMonthRegular className="panel-icon" /></div>
                {schoolEvents.map((event) => <div className="event-row" key={event.title}><div className="event-date">{event.date.split(" ")[0]}<Text size={200}>{event.date.split(" ")[1]}</Text></div><div><Text weight="semibold">{event.title}</Text><Text size={200}>{event.detail}</Text></div></div>)}
                <Button appearance="subtle">학사일정 전체 보기</Button>
              </div>
              <div className="panel preference-panel">
                <div className="panel-title"><div><Text className="eyebrow">맞춤 설정</Text><Subtitle1>놓치지 않도록 알려드릴게요</Subtitle1></div><MegaphoneLoudRegular className="panel-icon" /></div>
                <Switch checked={alertsEnabled} onChange={(_, data) => setAlertsEnabled(data.checked)} label="급식 변경·없음 알림" />
                <Field label="관심 영양·알레르기 키워드"><Input placeholder="예: 새우, 우유" value={allergyFilter} onChange={(_, data) => setAllergyFilter(data.value)} /></Field>
                <Text size={200} className="preference-help">입력한 키워드가 영양정보에 포함된 식단만 결과 카드에 표시돼요.</Text>
              </div>
            </section>
          </>
        ) : (
          <section className="panel analysis-placeholder">
            <SparkleRegular className="analysis-icon" />
            <Subtitle1>학교 급식 분석</Subtitle1>
            <Text>두 학교의 식단을 AI가 영양 균형과 메뉴 품질 관점에서 비교해 드려요.</Text>
            <Button appearance="primary">분석 시작하기</Button>
          </section>
        )}
        <MessageBar className="notice" intent="info">급식 정보는 NEIS 교육정보 개방 포털의 데이터를 기준으로 제공됩니다.</MessageBar>
      </main>
      <footer><Text size={200}>급식배틀 · 학교 점심 정보를 더 쉽고 즐겁게</Text></footer>
    </div>
  );
}

export default App;


createRoot(document.getElementById('root')!).render(<App />);




