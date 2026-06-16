import { NextResponse } from "next/server";

import { resolveDestinationFromToken } from "@/lib/auth/guard";
import { createClient } from "@/lib/supabase/server";

/** Google OAuth 콜백: 인가 코드를 세션으로 교환하고 역할 홈/온보딩으로 보낸다. */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  if (code) {
    const supabase = await createClient();
    const { data, error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error && data.session) {
      const dest = await resolveDestinationFromToken(data.session.access_token);
      return NextResponse.redirect(`${origin}${dest}`);
    }
  }

  return NextResponse.redirect(`${origin}/login`);
}
