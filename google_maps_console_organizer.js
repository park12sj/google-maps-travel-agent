/**
 * ==============================================================================
 * 📍 구글 지도 저장함 카테고리별 자동 재편 스크립트 (Google Maps Auto-Organizer)
 * ==============================================================================
 * 
 * [사용 방법]
 * 1. PC 브라우저(네이버 웨일, 크롬, 사파리 등)에서 구글 지도(https://www.google.com/maps)에 로그인합니다.
 * 2. 좌측 메뉴 [저장됨] -> [+ 새 목록]을 눌러 옮겨 담을 카테고리 목록들을 미리 만들어 둡니다.
 *    (기본 권장 목록 이름: "식당 및 카페", "숙박", "유적지 및 관광지", "쇼핑 및 시장", "기타")
 * 3. [저장됨] 화면에서 정리하고 싶은 기존 여행 목록(예: "2026 스페인 포르토 여행")을 클릭하여 들어갑니다.
 * 4. F12 키(또는 Mac: Cmd + Option + I)를 눌러 [개발자 도구]를 열고 상단 [Console(콘솔)] 탭을 누릅니다.
 * 5. 아래 코드 전체를 복사하여 콘솔에 붙여넣고 Enter를 누르면 자동으로 진행됩니다.
 * 
 * * 팁:
 *   - DRY_RUN: true 로 설정하면 실제로 변경하지 않고 어떻게 분류되는지 콘솔로 미리 확인합니다.
 *   - REMOVE_FROM_ORIGINAL: true 로 설정하면 새 카테고리 목록에 넣은 뒤 기존 여행 목록에서는 체크를 뺍니다.
 */

(async function startGoogleMapsOrganizer() {
  // ==========================================
  // 1. 사용자 설정 (필요시 수정)
  // ==========================================
  const CONFIG = {
    DRY_RUN: false,             // true: 시뮬레이션(미리보기만), false: 실제 저장 실행
    REMOVE_FROM_ORIGINAL: false, // true: 기존 여행 목록에서 제거, false: 기존 목록 유지(안전 모드)
    ACTION_DELAY_MS: 700,       // 클릭 및 화면 전환 대기 시간 (네트워크가 느리면 1000~1200으로 증액 권장)
    
    // 대상 목록 이름 (구글 지도에 생성한 목록 이름과 같아야 합니다)
    LIST_NAMES: {
      FOOD: "식당 및 카페",
      LODGING: "숙박",
      ATTRACTION: "유적지 및 관광지",
      SHOPPING: "쇼핑 및 시장",
      OTHER: "기타"
    }
  };

  // ==========================================
  // 2. 카테고리 매칭 규칙 (한국어 및 영어 지원)
  // ==========================================
  const RULES = [
    {
      category: CONFIG.LIST_NAMES.LODGING,
      keywords: [
        '호텔', '호스텔', '게스트하우스', '리조트', '민박', '펜션', '모텔', '여관', '숙소', '숙박', '비앤비',
        'hotel', 'hostel', 'resort', 'lodging', 'guest house', 'inn', 'bnb', 'motel', 'pousada', 'albergue'
      ]
    },
    {
      category: CONFIG.LIST_NAMES.FOOD,
      keywords: [
        '음식점', '식당', '레스토랑', '카페', '커피', '베이커리', '빵집', '제과점', '바', '주점', '펍', '와인바',
        '타파스', '비스트로', '피자', '파스타', '스테이크', '브런치', '디저트', '아이스크림', '패스트푸드',
        '스페인 요리', '이탈리아 요리', '프랑스 요리', '대만 요리', '한식', '일식', '중식', '해산물', '타코', '버거',
        '우육면', '라멘', '딤섬', '찻집', '치킨', '야시장',
        'restaurant', 'cafe', 'coffee', 'bakery', 'bar', 'pub', 'bistro', 'wine bar', 'tapas',
        'brunch', 'dessert', 'ice cream', 'pizza', 'pasta', 'food', 'diner', 'grill'
      ]
    },
    {
      category: CONFIG.LIST_NAMES.ATTRACTION,
      keywords: [
        '관광 명소', '명소', '역사적 명소', '유적지', '성당', '교회', '사찰', '절', '모스크', '신사',
        '박물관', '미술관', '궁전', '성', '기념비', '전망대', '탑', '광장', '극장', '오페라', '문화재', '유네스코',
        '대성당', '수도원', '고궁', '케이블카', '유람선', '랜드마크',
        'tourist attraction', 'historical landmark', 'landmark', 'museum', 'art museum',
        'cathedral', 'church', 'basilica', 'monastery', 'castle', 'palace', 'monument', 'observation deck', 'tower', 'plaza', 'square'
      ]
    },
    {
      category: CONFIG.LIST_NAMES.SHOPPING,
      keywords: [
        '쇼핑몰', '시장', '마켓', '백화점', '기념품', '아울렛', '마트', '슈퍼마켓', '상점',
        'shopping mall', 'market', 'department store', 'souvenir', 'outlet', 'supermarket', 'store'
      ]
    }
  ];

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function printLog(msg, color = "#1a73e8") {
    console.log(`%c[구글지도 정리기] ${msg}`, `color: ${color}; font-weight: bold; font-size: 12px;`);
  }

  function classifyPlace(subText, title) {
    const combined = `${subText} ${title}`.toLowerCase();
    for (const rule of RULES) {
      for (const kw of rule.keywords) {
        if (combined.includes(kw.toLowerCase())) {
          return rule.category;
        }
      }
    }
    return CONFIG.LIST_NAMES.OTHER;
  }

  printLog(`🚀 구글 지도 저장함 자동 재편 작업을 시작합니다! (시뮬레이션 모드: ${CONFIG.DRY_RUN})`, "#1a73e8");

  // 1. 목록 스크롤을 끝까지 내려 모든 장소 DOM 로드
  const scrollContainer = document.querySelector('div[role="feed"]') || 
                          document.querySelector('div.m6QErb[aria-label]') || 
                          document.querySelector('div[role="main"]') ||
                          document.querySelector('.m6QErb');
  
  if (scrollContainer) {
    printLog("📜 목록 전체를 불러오기 위해 자동 스크롤을 진행합니다...", "#5f6368");
    let lastHeight = scrollContainer.scrollHeight;
    for (let i = 0; i < 15; i++) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
      await sleep(400);
      if (scrollContainer.scrollHeight === lastHeight && i > 3) break;
      lastHeight = scrollContainer.scrollHeight;
    }
    scrollContainer.scrollTop = 0;
    await sleep(500);
  }

  // 2. 장소 카드 수집
  const cards = Array.from(document.querySelectorAll('div[role="article"], div[jsaction*="placeCard"], div.fontHeadlineSmall')).map(el => {
    return el.closest('div[role="article"]') || el.closest('div[jsaction*="placeCard"]') || el.parentElement;
  }).filter((v, i, a) => v && a.indexOf(v) === i && (v.querySelector('.fontHeadlineSmall, h2') || v.textContent.trim().length > 0));

  if (cards.length === 0) {
    printLog("❌ 현재 열려있는 목록에서 저장된 장소를 찾을 수 없습니다.", "#ea4335");
    printLog("👉 구글 지도 좌측 [저장됨] 메뉴에서 정리할 목록(예: '2026 스페인 포르토 여행')을 클릭해 연 뒤 다시 실행해주세요.", "#ea4335");
    return;
  }

  printLog(`총 ${cards.length}개의 장소를 찾았습니다. 분류 작업을 진행합니다.\n`, "#34a853");

  const summary = {};
  let successCount = 0;

  for (let idx = 0; idx < cards.length; idx++) {
    const card = cards[idx];

    // 카드 내 장소명 및 업종 정보 추출
    const titleEl = card.querySelector('.fontHeadlineSmall') || card.querySelector('h2') || card.querySelector('div[role="button"]');
    const placeName = titleEl ? titleEl.textContent.trim() : `장소 #${idx + 1}`;
    
    // 업종 태그(예: "성당 · 4.7 ★", "스페인 요리") 추출
    const spans = Array.from(card.querySelectorAll('span, div.fontBodyMedium, div.fontBodySmall'));
    let subText = "";
    for (const span of spans) {
      const txt = span.textContent.trim();
      if (txt && !txt.includes('★') && !txt.match(/^\d+(\.\d+)?$/) && txt.length < 40 && txt !== placeName) {
        subText = txt.replace(/^·\s*/, '');
        break;
      }
    }

    const targetCategory = classifyPlace(subText, placeName);
    summary[targetCategory] = (summary[targetCategory] || 0) + 1;

    printLog(`[${idx + 1}/${cards.length}] "${placeName}" (${subText || '태그 없음'}) ➔ 분류: [${targetCategory}]`, "#f2994a");

    if (CONFIG.DRY_RUN) {
      continue;
    }

    try {
      // 장소 카드 클릭 -> 상세 화면 열기
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await sleep(CONFIG.ACTION_DELAY_MS / 2);

      const clickable = card.querySelector('button, a, div[role="button"]') || card;
      clickable.click();
      await sleep(CONFIG.ACTION_DELAY_MS * 1.5);

      // '저장' 버튼 찾기 (저장됨 / Save / Saved)
      const saveBtn = Array.from(document.querySelectorAll('button[data-value*="Save"], button[data-value*="저장"], button[aria-label*="저장"], button[aria-label*="Save"]'))
        .find(b => b.offsetWidth > 0 && b.offsetHeight > 0);

      if (!saveBtn) {
        printLog(`  ⚠️ "${placeName}" 상세 패널에서 저장 버튼을 찾지 못해 건너뜁니다.`, "#ea4335");
        // 뒤로가기 시도
        const backBtn = document.querySelector('button[aria-label*="뒤로"], button[aria-label*="Back"], button[jsaction*="back"]');
        if (backBtn) backBtn.click();
        await sleep(CONFIG.ACTION_DELAY_MS);
        continue;
      }

      saveBtn.click();
      await sleep(CONFIG.ACTION_DELAY_MS);

      // 저장 목록 팝업 내 대상 체크박스 탐색
      const menuItems = Array.from(document.querySelectorAll('div[role="menuitemcheckbox"], div[role="menuitemradio"], div[role="checkbox"], div[role="dialog"] label, div[role="menu"] label'));
      
      let targetItem = null;
      for (const item of menuItems) {
        if (item.textContent.includes(targetCategory)) {
          targetItem = item;
          break;
        }
      }

      if (targetItem) {
        const isChecked = targetItem.getAttribute('aria-checked') === 'true' || targetItem.querySelector('input[type="checkbox"]:checked');
        if (!isChecked) {
          targetItem.click();
          printLog(`  ✅ [${targetCategory}] 목록에 저장 완료!`, "#34a853");
          await sleep(CONFIG.ACTION_DELAY_MS);
        } else {
          printLog(`  ℹ️ 이미 [${targetCategory}] 목록에 저장되어 있습니다.`, "#5f6368");
        }
      } else {
        printLog(`  ⚠️ [${targetCategory}] 목록이 구글 지도에 없습니다. 먼저 해당 이름으로 목록을 생성해주세요.`, "#ea4335");
      }

      // 팝업 닫기 (ESC)
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
      await sleep(CONFIG.ACTION_DELAY_MS / 2);

      // 상세 패널 뒤로가기 버튼 클릭하여 다시 목록으로 복귀
      const backBtn = document.querySelector('button[aria-label*="뒤로"], button[aria-label*="Back"], button[jsaction*="back"]');
      if (backBtn && backBtn.offsetWidth > 0) {
        backBtn.click();
        await sleep(CONFIG.ACTION_DELAY_MS);
      }

      successCount++;
    } catch (err) {
      printLog(`  ❌ 처리 중 오류 발생: ${err.message}`, "#ea4335");
    }

    await sleep(CONFIG.ACTION_DELAY_MS / 2);
  }

  printLog(`\n🎉 모든 작업이 완료되었습니다! (성공: ${successCount}건)`, "#34a853");
  console.table(summary);
})();
