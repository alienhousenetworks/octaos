export const PEOPLE_ROUTES = {
  people: '/app/hr',
  hiring: '/app/hr/hiring',
  leave: '/app/hr/leave',
} as const;

export type PeopleScreen = keyof typeof PEOPLE_ROUTES;

export function peopleScreenFromPath(pathname: string): PeopleScreen {
  if (pathname.startsWith('/app/hr/leave')) return 'leave';
  if (pathname.startsWith('/app/hr/hiring') || pathname.startsWith('/app/hiring')) return 'hiring';
  return 'people';
}
