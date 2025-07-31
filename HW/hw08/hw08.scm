(define (ascending? s)
  (if (or (null? s) (null? (cdr s)))
    #t
    (if (> (car s) (car (cdr s)))
      #f
      (ascending? (cdr s)))))

(define (my-filter pred s)
  (if (null? s)
    (list)
    (if (pred (car s))
      (append (list (car s)) (my-filter pred (cdr s)))
      (my-filter pred (cdr s)))))

(define (interleave lst1 lst2)
  (cond
    ((null? lst1) lst2)
    ((null? lst2) lst1)
    (else (append (list (car lst1)) (list(car lst2)) (interleave (cdr lst1) (cdr lst2))))))

(define (no-repeats s)
  (if (null? s)
    (list)
    (append (list (car s)) (filter (lambda (x) (not (= x (car s)))) (no-repeats (cdr s))))))
