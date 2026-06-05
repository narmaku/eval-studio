// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
}
