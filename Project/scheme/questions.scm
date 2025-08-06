(define (caar x) (car (car x)))
(define (cadr x) (car (cdr x)))
(define (cdar x) (cdr (car x)))
(define (cddr x) (cdr (cdr x)))

;; Problem 15
;; Returns a list of two-element lists
(define (enumerate s)
  (define (helper lst index)
    (if (null? lst)
        '()
        (cons (list index (car lst))
              (helper (cdr lst) (+ index 1)))))
  (helper s 0))
  ; END PROBLEM 15

;; Problem 16

;; Merge two lists S1 and S2 according to ORDERED? and return
;; the merged lists.
(define (merge ordered? lst1 lst2)
  (cond ((null? lst1) lst2) ; 基本情况1: 如果 lst1 为空, 返回 lst2
        ((null? lst2) lst1) ; 基本情况2: 如果 lst2 为空, 返回 lst1
        (else
         (let ((head1 (car lst1))
               (head2 (car lst2)))
           (if (ordered? head1 head2)
               ; 如果 head1 应排在 head2 前面，
               ; 则将 head1 作为结果的第一个元素，
               ; 然后递归地合并 lst1 的剩余部分和整个 lst2
               (cons head1 (merge ordered? (cdr lst1) lst2))
               ; 否则，将 head2 作为结果的第一个元素，
               ; 然后递归地合并整个 lst1 和 lst2 的剩余部分
               (cons head2 (merge ordered? lst1 (cdr lst2))))))))
  ; END PROBLEM 16

;; Optional Problem 2

;; Returns a function that checks if an expression is the special form FORM
(define (check-special form)
  (lambda (expr) (equal? form (car expr))))

(define lambda? (check-special 'lambda))
(define define? (check-special 'define))
(define quoted? (check-special 'quote))
(define let?    (check-special 'let))

;; Converts all let special forms in EXPR into equivalent forms using lambda
(define (let-to-lambda expr)
  (cond ((atom? expr)
         ; BEGIN OPTIONAL PROBLEM 2
         'replace-this-line
         ; END OPTIONAL PROBLEM 2
         )
        ((quoted? expr)
         ; BEGIN OPTIONAL PROBLEM 2
         'replace-this-line
         ; END OPTIONAL PROBLEM 2
         )
        ((or (lambda? expr)
             (define? expr))
         (let ((form   (car expr))
               (params (cadr expr))
               (body   (cddr expr)))
           ; BEGIN OPTIONAL PROBLEM 2
           'replace-this-line
           ; END OPTIONAL PROBLEM 2
           ))
        ((let? expr)
         (let ((values (cadr expr))
               (body   (cddr expr)))
           ; BEGIN OPTIONAL PROBLEM 2
           'replace-this-line
           ; END OPTIONAL PROBLEM 2
           ))
        (else
         ; BEGIN OPTIONAL PROBLEM 2
         'replace-this-line
         ; END OPTIONAL PROBLEM 2
         )))

; Some utility functions that you may find useful to implement for let-to-lambda

(define (zip pairs)
  'replace-this-line)
