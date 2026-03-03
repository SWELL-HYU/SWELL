"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getMe } from "@/lib/auth";
import { User } from "@/types/api";


export function useAuth(requireAuth: boolean = true) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkAuth() {
      const token = sessionStorage.getItem("token");

      // 토큰 없으면
      if (!token) {
        setLoading(false);
        if (requireAuth) {
          router.push("/start");
        }
        return;
      }

      // 토큰 있으면 유저 정보 조회
      try {
        const response = await getMe();
        if (response.success && response.data.user) {
          setUser(response.data.user);
        } else {
          sessionStorage.removeItem("token");
          if (requireAuth) {
            router.push("/start");
          }
        }
      } catch (error) {
        sessionStorage.removeItem("token");
        if (requireAuth) {
          router.push("/start");
        }
      } finally {
        setLoading(false);
      }
    }

    checkAuth();
  }, [requireAuth, router]);

  return { user, loading, setUser };
}