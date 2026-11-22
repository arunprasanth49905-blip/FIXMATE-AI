import { Project } from '../types/api';

/**
 * Normalizes a project name for comparison and duplicate detection:
 * - Trims leading and trailing whitespace.
 * - Converts to lowercase for case-insensitive comparison.
 * - Collapses internal consecutive whitespace to a single space.
 */
export function normalizeProjectName(name: string | null | undefined): string {
  if (!name || typeof name !== 'string') return '';
  return name.trim().split(/\s+/).join(' ').toLowerCase();
}

/**
 * Checks whether a given project name is a duplicate among a list of projects.
 * @param name The proposed project name
 * @param existingProjects The list of existing projects
 * @param excludeProjectId Optional project ID to exclude (e.g. current project during rename)
 */
export function isProjectNameDuplicate(
  name: string,
  existingProjects: Project[],
  excludeProjectId?: string
): boolean {
  const norm = normalizeProjectName(name);
  if (!norm) return false;

  return existingProjects.some((p) => {
    if (excludeProjectId && p.id === excludeProjectId) {
      return false;
    }
    return normalizeProjectName(p.name) === norm;
  });
}
