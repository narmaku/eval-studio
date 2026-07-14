import { useEffect, useState } from 'react';

import { api } from '@/services/api';

declare const __APP_VERSION__: string;

const BUILD_VERSION: string = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.0.0';

/**
 * Returns the application version.
 *
 * Starts with the build-time version injected by Vite from package.json,
 * then updates with the authoritative version from the backend health
 * endpoint once it responds.
 */
export function useAppVersion(): string {
  const [version, setVersion] = useState<string>(BUILD_VERSION);

  useEffect(() => {
    let cancelled = false;

    api
      .getHealth()
      .then((data) => {
        if (!cancelled && data.version) {
          setVersion(data.version);
        }
      })
      .catch(() => {
        // Keep the build-time version on failure
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return version;
}
